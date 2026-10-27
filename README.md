# WindPulse — UK Wind Generation Forecast Evaluation Platform

WindPulse is a full-stack web application for evaluating UK wind power generation forecasts against actual generation data. It retrieves data from the Elexon BMRS API, aligns forecasts with actual generation, and presents evaluation metrics through an interactive dashboard.

## Live Application

- **Frontend:** https://windpulse-rho.vercel.app/
- **Backend API:** https://wind-pulse-two.vercel.app/
- **API Documentation:** https://wind-pulse-two.vercel.app/docs
- **Health Check:** https://wind-pulse-two.vercel.app/health

## Overview

WindPulse helps users understand how closely day-ahead wind generation forecasts match actual generation.

The application retrieves UK wind generation data, processes the available records, calculates forecast accuracy metrics, and displays the results through charts, summary cards, and tables.

### Key Features

- Retrieve actual wind generation data from the Elexon BMRS API.
- Retrieve day-ahead wind generation forecasts.
- Align actual and forecast records by their timestamps.
- Evaluate forecast accuracy using standard statistical metrics.
- Display actual and forecast generation in interactive charts.
- Filter and explore evaluation results by date.
- Show data coverage and matched-record information.
- Provide REST API endpoints for accessing wind data and evaluation results.
- Support local development and cloud deployment.

## Architecture

WindPulse uses a separate frontend and backend architecture.

```text
                 ┌────────────────────────┐
                 │      React Frontend     │
                 │  TypeScript + Vite      │
                 └────────────┬───────────┘
                              │ HTTP requests
                              ▼
                 ┌────────────────────────┐
                 │      FastAPI Backend    │
                 │  Data Processing        │
                 │  Forecast Evaluation    │
                 └────────────┬───────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │    Elexon BMRS API      │
                 │ Actuals and Forecasts   │
                 └────────────────────────┘
```

### Forecast Evaluation Metrics

| Metric | Description |
|---|---|
| MAE | Mean Absolute Error between actual and forecast generation |
| RMSE | Root Mean Squared Error, which gives greater weight to larger errors |
| Bias | Average signed forecast error, indicating systematic over- or under-forecasting |
| nMAE | Normalized Mean Absolute Error |
| MAPE | Mean Absolute Percentage Error, subject to limitations when actual values are zero or near zero |
| Coverage | Percentage of expected periods with usable matched data |

The exact interpretation of bias depends on the application's sign convention. Refer to the API response and implementation for the precise definition.

## Technology Stack

### Frontend

- React
- TypeScript
- Vite
- Material UI (MUI)
- Recharts
- Axios
- Vitest
- React Testing Library

### Backend

- Python 3.11+
- FastAPI
- Uvicorn
- Pydantic
- HTTPX
- Pytest
- Pytest-Asyncio

### Data Source and Deployment

- Elexon BMRS API
- Vercel for frontend and backend deployment
- Git and GitHub for version control

## AI Tools Used

The following AI-assisted development tools were used during the development process:

### ChatGPT

Used as a development assistant for:
- Understanding project requirements and breaking them into manageable tasks.
- Explaining technical concepts and debugging approaches.
- Reviewing implementation ideas and suggesting improvements.
- Assisting with API integration, testing, documentation, and deployment troubleshooting.

### Antigravity CLI

Used as an AI-assisted development tool for:
- Supporting backend development and implementation tasks.
- Helping investigate code issues and troubleshoot errors.
- Assisting with code changes based on project requirements.
- Supporting development workflows and validation.

AI tools were used to assist development. The application's functionality, configuration, and test results should be verified against the actual source code and deployment.

## Repository Structure

```text
WindPulse/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── ...
│   ├── tests/
│   ├── requirements.txt
│   └── .python-version
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

*Note: The tree above highlights the main areas of the project. Individual files may differ as the implementation evolves.*

## Prerequisites

Install the following before running the project locally:

- Python 3.11 or later
- Node.js and npm
- Git

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/nithinr8265/WindPulse.git
cd WindPulse
```

### 2. Set Up the Backend

Open a terminal in the repository root.

Create and activate a virtual environment:

**Windows PowerShell**

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Configure the backend environment variables using the variables required by the application's settings. Keep secrets in a local `.env` file and never commit real credentials.

Start the API server from the `backend` directory:

```bash
uvicorn app.main:app --reload
```

The local backend should be available at:

- API: http://127.0.0.1:8000
- Swagger documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

### 3. Set Up the Frontend

Open a second terminal:

```bash
cd frontend
npm install
```

Create or update the frontend environment file as needed:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the development server:

```bash
npm run dev
```

Open the local URL printed by Vite in the terminal.

## API Endpoints

The backend exposes the following main endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check API health |
| GET | `/api/v1/wind/actuals` | Retrieve actual wind generation data |
| GET | `/api/v1/wind/forecasts` | Retrieve wind generation forecasts |
| GET | `/api/v1/wind/evaluation` | Retrieve forecast evaluation results |

For supported query parameters, request formats, and response schemas, see the interactive [API documentation](https://wind-pulse-two.vercel.app/docs).

## Testing

### Backend Tests

Run from the `backend` directory with the virtual environment activated:

```bash
pytest
```

### Frontend Tests

Run from the `frontend` directory:

```bash
npm test
```

### Frontend Type Checking

```bash
npx tsc --noEmit
```

### Frontend Production Build

```bash
npm run build
```

Run the relevant checks after making changes to verify that the application continues to work as expected.

## Environment Variables

### Frontend

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Base URL used by the frontend to communicate with the backend API |

For local development, use `http://127.0.0.1:8000`. For the deployed frontend, use `https://wind-pulse-two.vercel.app`.

### Backend

Configure the variables required by the backend settings, such as the application environment and allowed frontend origins.

| Variable | Purpose |
|---|---|
| `APP_ENV` | Identifies the application environment, such as development or production |
| `ALLOWED_ORIGINS` | Specifies the frontend origins allowed to access the API through browser CORS |

Use the backend's actual settings implementation as the source of truth for required variables and accepted formats.

For deployment, configure variables in the relevant Vercel project's settings and redeploy after making changes.

## Deployment

WindPulse is deployed as two separate Vercel projects:

- **Frontend project:** serves the React application.
- **Backend project:** serves the FastAPI application.

The frontend uses `VITE_API_BASE_URL` to communicate with the deployed backend. The backend must allow the deployed frontend origin through its CORS configuration.

Environment variables are applied to new deployments, so redeploy the relevant project after updating them. See the [Vercel environment variables documentation](https://vercel.com/docs/environment-variables) for details.

## Security and Best Practices

- Do not commit `.env` files, API keys, passwords, or other secrets.
- Keep private backend configuration separate from public frontend configuration.
- Validate API inputs and handle external API failures appropriately.
- Use the configured CORS allowlist instead of allowing arbitrary origins.
- Test changes locally before deploying them.

## Troubleshooting

**Frontend cannot connect to the backend**
- Verify `VITE_API_BASE_URL`.
- Confirm that the backend health endpoint is responding.
- Check the backend CORS configuration and browser console.

**Backend fails to start**
- Confirm the Python version and virtual environment.
- Install dependencies from `requirements.txt`.
- Check the terminal output for missing configuration or import errors.

**No data or incomplete evaluation results**
- Check the backend API response and external data availability.
- Verify the selected date and supported query parameters.
- Review matched-record counts and coverage before interpreting the metrics.

---

**WindPulse** — A full-stack platform for UK wind generation forecast evaluation.
