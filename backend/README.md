# WindPulse Wind Forecast Evaluation API

A Python REST API built with **FastAPI, Pydantic v2, and HTTPX** to retrieve, match, and evaluate UK wind generation forecasts against actual generation data from the Elexon BMRS API.

The backend applies a configurable day-ahead forecast selection rule, calculates forecast accuracy metrics, and reports data coverage without fabricating missing observations.

## Table of Contents

- [Overview and Architecture](#overview-and-architecture)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Day-Ahead Decision Rule](#day-ahead-decision-rule)
- [Accuracy Metrics](#accuracy-metrics)
- [Environment Variables](#environment-variables)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [API Endpoints](#api-endpoints)
- [Docker Deployment](#docker-deployment)
- [Frontend Integration](#frontend-integration)
- [AI Tools Used](#ai-tools-used)
- [Security Considerations](#security-considerations)

## Overview and Architecture

Electricity generation forecasts can help analysts understand expected wind power output. Evaluating these forecasts against actual generation requires consistent timestamps, clear forecast selection rules, and reliable error calculations.

WindPulse provides an API that:

1. Retrieves actual wind generation and forecast records from Elexon BMRS.
2. Filters forecasts using a configurable day-ahead decision cutoff.
3. Selects the latest eligible forecast for each target delivery timestamp.
4. Matches forecasts with actual observations.
5. Calculates accuracy metrics in megawatts and percentages.
6. Reports matched, missing, and unmatched records.

### Architecture

```text
                 Elexon BMRS API
                  /            \
                 /              \
          FUELHH Actuals     WINDFOR Forecasts
                 |              |
                 |       Decision Cutoff Filter
                 |              |
                 |       Latest Eligible Forecast
                 |              |
                 +-------+------+
                         |
                  Timestamp Matching
                         |
                  Accuracy Metrics
                         |
                    FastAPI REST API
                         |
             React Frontend / API Clients
```

The application uses the `FUELHH` dataset for half-hourly generation outturn and `WINDFOR` for wind generation forecasts. See the [official Elexon API documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint).

## Key Features

- **FastAPI REST API:** Provides endpoints with automatically generated OpenAPI documentation.
- **Pydantic v2:** Supports typed data models and validation.
- **Asynchronous HTTP requests:** Uses HTTPX to communicate with the external API.
- **Forecast cutoff filtering:** Excludes forecasts published after the configured decision cutoff.
- **Latest forecast selection:** Chooses the most recently published eligible forecast for each target timestamp.
- **Forecast and actual matching:** Matches records using their target delivery timestamps.
- **Accuracy metrics:** Calculates MAE, RMSE, bias, nMAE, and MAPE.
- **Missing-data reporting:** Tracks unmatched observations without synthetic interpolation.
- **Configurable CORS:** Allows approved frontend origins to access the API.
- **Automated tests:** Supports unit and API tests using pytest.
- **Docker support:** Includes a container configuration for running the backend.

## Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python 3.11+ |
| API framework | FastAPI |
| Data validation | Pydantic v2 |
| HTTP client | HTTPX |
| ASGI server | Uvicorn |
| Configuration | Pydantic Settings and environment variables |
| Testing | Pytest and pytest-asyncio |
| External data | Elexon BMRS API |
| Containerization | Docker |
| Version control | Git and GitHub |

## Project Structure

```text
backend/
├── .env.example
├── .gitignore
├── .python-version
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── clients/
│   │   ├── __init__.py
│   │   └── elexon_client.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   └── services/
│       ├── __init__.py
│       ├── forecast_service.py
│       └── metrics_service.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_forecast_selection.py
    ├── test_metrics.py
    └── test_routes.py
```

The structure above represents the main application modules. The exact files and available tests may vary with the current repository version.

## Day-Ahead Decision Rule

### 1. Configurable cutoff

WindPulse uses a configurable cutoff to determine which forecasts are eligible for evaluation.

For a target delivery date \(D\), the default application rule is:

\[
\text{Cutoff}(D) = (D-1)\text{ at 12:00 UTC}
\]

The default cutoff hour is `12`, configurable through `DAY_AHEAD_DECISION_CUTOFF_HOUR` or the `cutoff_hour` query parameter on the evaluation endpoint.

**Important:** This is the application's configured evaluation rule. It should not be interpreted as a universal statement of every Great Britain market's auction deadline.

### 2. Forecast selection

For each target delivery timestamp, the service considers forecasts published at or before the applicable cutoff and selects the latest eligible publication.

\[
f^* = \arg\max_{f \in F,\;p_f \leq C} p_f
\]

Where:

- \(F\) is the set of forecasts for a target delivery timestamp.
- \(p_f\) is the publication timestamp of a forecast.
- \(C\) is the configured cutoff.
- \(f^*\) is the selected forecast.

Forecasts published after the cutoff are excluded from that evaluation.

### 3. Timestamp matching and missing data

The actual generation dataset is half-hourly, while the forecast dataset is hourly in the evaluation workflow described here.

The service matches records according to the implementation's timestamp matching rules. Where no eligible forecast or corresponding actual record exists, the missing observation is reported rather than fabricated or interpolated.

For January 2026, a complete half-hourly actual series contains 1,488 periods, while an hourly series contains 744 periods. These are expected counts for the calendar month, not a guarantee that the API will return every record.

## Accuracy Metrics

The metrics use matched actual and forecast observations. Generation and absolute error values are expressed in megawatts (MW).

Let:

- \(y_i\) be the actual generation.
- \(\hat{y}_i\) be the forecast generation.
- \(N\) be the number of matched observations.
- \(e_i = \hat{y}_i-y_i\) be the signed forecast error.

| Metric | Formula | Interpretation |
|---|---|---|
| MAE | \(\frac{1}{N}\sum_{i=1}^{N}|e_i|\) | Average absolute forecast error in MW |
| RMSE | \(\sqrt{\frac{1}{N}\sum_{i=1}^{N}e_i^2}\) | Error measure that gives greater weight to larger errors |
| Bias | \(\frac{1}{N}\sum_{i=1}^{N}e_i\) | Signed average error; positive indicates over-forecasting |
| nMAE | \(\frac{\mathrm{MAE}}{\bar{y}}\times100\%\) | MAE normalized by mean actual generation |
| MAPE | \(\frac{100\%}{N_{nz}}\sum_{y_i>0}\frac{|e_i|}{y_i}\) | Mean absolute percentage error for positive actual values |

Here, \(N_{nz}\) is the number of matched observations with positive actual generation.

Percentage metrics can be misleading when actual generation is zero or close to zero. The implementation's handling of these cases should be checked when interpreting results.

## Environment Variables

Create a local environment file from the template:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS/Linux**

```bash
cp .env.example .env
```

Configure the variables supported by the backend settings.

| Variable | Typical default | Purpose |
|---|---|---|
| `APP_NAME` | `WindPulse Wind Forecast Evaluation API` | Application name |
| `APP_ENV` | `development` | Application environment |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Elexon API base URL |
| `HTTP_TIMEOUT_SECONDS` | `30.0` | External request timeout |
| `DAY_AHEAD_DECISION_CUTOFF_HOUR` | `12` | Configured cutoff hour in UTC |
| `ALLOWED_ORIGINS` | Local frontend origins | Comma-separated CORS origin allowlist |

The defaults above describe the intended configuration. Confirm the actual defaults, validation rules, and accepted formats in `app/config.py` and `.env.example` before changing deployment settings.

Do not commit real credentials or private environment values.

## Getting Started

### Prerequisites

- Python 3.11 or a compatible version supported by the project.
- Git.
- PowerShell on Windows, or a terminal on macOS/Linux.

### 1. Navigate to the backend

From PowerShell:

```powershell
cd C:\windpulse\backend
```

### 2. Create a virtual environment

```powershell
py -3.11 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use a permitted activation method for your environment rather than changing system security settings unnecessarily.

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure the application

Create `.env` from `.env.example` and review the supported configuration values.

For local development, make sure the backend's CORS configuration allows the frontend's origin, such as `http://localhost:5173`, if that is the port used by Vite.

### 5. Start the API

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The local API should be available at:

- Base URL: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health check: http://127.0.0.1:8000/health

## Running Tests

Run the default test suite from the backend directory with the virtual environment activated:

```powershell
python -m pytest -v
```

The default tests should use mocked external responses where configured, allowing isolated tests to run without depending on live API availability.

If the repository includes optional live Elexon reconciliation tests, follow their implementation and configuration instructions before enabling them. Live tests may depend on network access and current external data.

Do not assume a fixed test count: use the test output from the current repository version as the source of truth.

## API Endpoints

The following endpoints are part of the documented API.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check backend status |
| GET | `/api/v1/wind/actuals` | Retrieve actual wind generation |
| GET | `/api/v1/wind/forecasts` | Retrieve wind forecasts |
| GET | `/api/v1/wind/evaluation` | Retrieve forecast evaluation results |

Use the interactive documentation at `/docs` to confirm supported parameters, response schemas, and validation rules.

### 1. Health check

```powershell
curl.exe http://127.0.0.1:8000/health
```

Example response:

```json
{
  "status": "ok",
  "app_name": "WindPulse Wind Forecast Evaluation API",
  "timestamp": "2026-01-01T00:00:00Z",
  "environment": "development"
}
```

The timestamp and environment shown here are illustrative; the running application returns its current values.

### 2. Actual wind generation

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/wind/actuals?from_date=2026-01-01&to_date=2026-01-02&limit=2"
```

This endpoint retrieves actual generation records for the requested date range. Check `/docs` for the precise response fields and accepted parameters.

### 3. Raw wind forecasts

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/wind/forecasts?from_date=2026-01-01&to_date=2026-01-01&limit=2"
```

This endpoint retrieves forecast records for the selected target delivery dates. Forecast publication timestamps and target delivery timestamps are distinct and should not be confused.

### 4. Forecast evaluation

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/wind/evaluation?from_date=2026-01-01&to_date=2026-01-31&include_timeseries=false"
```

The evaluation endpoint applies the configured cutoff and returns summary information and accuracy metrics. Set `include_timeseries=false` when only the summary is needed, if supported by the current endpoint schema.

You can also specify a cutoff hour if the endpoint supports it:

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/wind/evaluation?from_date=2026-01-01&to_date=2026-01-31&cutoff_hour=12&include_timeseries=false"
```

Actual response fields and numerical results depend on the API implementation and available source data. Use the live Swagger documentation rather than relying on illustrative values in this README.

## Docker Deployment

If Docker is installed and the repository's `Dockerfile` is configured for the backend, build the image from the backend directory:

```powershell
docker build -t windpulse-backend .
```

Run the container:

```powershell
docker run --rm -p 8000:8000 --name windpulse-backend windpulse-backend
```

Check the health endpoint:

```powershell
curl.exe http://127.0.0.1:8000/health
```

If the application requires environment variables at runtime, supply them through your deployment configuration or a local environment file that is not committed to Git. Confirm the Dockerfile's entry point and configuration requirements before deploying.

## Frontend Integration

The React frontend can communicate with the backend over HTTP.

### CORS

Configure `ALLOWED_ORIGINS` to include the frontend origin, such as:

```text
http://localhost:5173
```

For production, add the exact deployed frontend origin. Avoid allowing arbitrary origins when credentials or sensitive data are involved.

### Dashboard performance

For dashboard summary cards, use the evaluation endpoint's summary-only option if it is supported. This can reduce the amount of time-series data transferred.

### Charts

When the API returns matched time-series records, the frontend can use them to display:

- Actual versus forecast generation.
- Forecast errors over time.
- Summary metrics such as MAE, RMSE, and bias.
- Matched-data coverage and missing observations.

Always use the response schema documented by the running backend.

## AI Tools Used

AI-assisted tools were used as development aids during implementation.

### ChatGPT

Used to assist with:

- Understanding project requirements and backend concepts.
- Breaking implementation tasks into manageable steps.
- Troubleshooting errors and exploring possible fixes.
- Reviewing documentation and improving explanations.
- Supporting test planning and deployment troubleshooting.

### Antigravity CLI

Used as an AI-assisted development tool to support:

- Backend implementation tasks.
- Code investigation and debugging.
- Development workflow assistance.
- Reviewing changes against project requirements.

AI-generated suggestions were used as development assistance. The implementation, configuration, and test results should be validated against the actual code and running application.

## Security Considerations

- Keep `.env` and other files containing secrets out of version control.
- Never publish API keys, passwords, access tokens, or private deployment configuration.
- Restrict CORS to the frontend origins that need access.
- Validate incoming query parameters and handle external API failures.
- Do not fabricate missing generation or forecast records.
- Review logs and error responses to ensure they do not expose secrets.

## Data Source

WindPulse uses the [Elexon BMRS API](https://bmrs.elexon.co.uk/api-documentation/endpoint) for UK electricity market data, including:

- `FUELHH` — half-hourly generation outturn by fuel type.
- `WINDFOR` — wind generation forecast data.

Refer to the official Elexon documentation for dataset definitions, available endpoints, and data limitations.

---

**WindPulse Wind Forecast Evaluation API** — A Python backend for evaluating UK wind generation forecasts against actual generation data.
