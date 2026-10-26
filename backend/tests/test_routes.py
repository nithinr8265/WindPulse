"""Integration and route tests for FastAPI endpoints with mocked Elexon client."""

from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_elexon_client
from app.clients.elexon_client import ElexonAPIError, ElexonClient
from app.main import app
from app.models.schemas import WindActualRecord, WindForecastRecord


@pytest.fixture
def mock_client_dependency(
    sample_actuals: List[WindActualRecord],
    sample_forecasts: List[WindForecastRecord],
):
    """Override the get_elexon_client FastAPI dependency with an AsyncMock."""
    mock_client = AsyncMock(spec=ElexonClient)
    mock_client.fetch_actual_wind_generation.return_value = sample_actuals
    mock_client.fetch_wind_forecasts.return_value = sample_forecasts

    app.dependency_overrides[get_elexon_client] = lambda: mock_client
    yield mock_client
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Tests for the /health route."""

    def test_health_check_returns_ok(self, test_client: TestClient):
        response = test_client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert "app_name" in payload
        assert "timestamp" in payload
        assert "environment" in payload


class TestActualsEndpoint:
    """Tests for the /api/v1/wind/actuals route."""

    def test_get_actuals_success(self, test_client: TestClient, mock_client_dependency):
        response = test_client.get("/api/v1/wind/actuals?from_date=2026-01-01&to_date=2026-01-02")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["count"] == 4
        assert len(payload["data"]) == 4
        assert payload["data"][0]["fuelType"] == "WIND"

    def test_get_actuals_with_limit(self, test_client: TestClient, mock_client_dependency):
        response = test_client.get("/api/v1/wind/actuals?from_date=2026-01-01&to_date=2026-01-02&limit=2")
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 2
        assert len(payload["data"]) == 2


class TestForecastsEndpoint:
    """Tests for the /api/v1/wind/forecasts route."""

    def test_get_forecasts_success(self, test_client: TestClient, mock_client_dependency):
        response = test_client.get("/api/v1/wind/forecasts?from_date=2026-01-01&to_date=2026-01-02")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["count"] == 6
        assert len(payload["data"]) == 6


class TestEvaluationEndpoint:
    """Tests for the /api/v1/wind/evaluation route."""

    def test_evaluate_forecasts_success(self, test_client: TestClient, mock_client_dependency):
        response = test_client.get("/api/v1/wind/evaluation?from_date=2026-01-01&to_date=2026-01-02")
        assert response.status_code == 200
        payload = response.json()

        assert payload["status"] == "success"
        assert "summary" in payload
        assert "metrics" in payload
        assert "matchedData" in payload

        summary = payload["summary"]
        assert summary["totalExpectedHourlyPeriods"] == 48  # 2 days * 24 hours
        assert summary["totalActualHalfHourlyPeriods"] == 96  # 2 days * 48 half-hours
        assert summary["totalExpectedPeriods"] == 48
        assert summary["matchedCount"] == 3
        assert summary["unmatchedHalfHourlyActualsCount"] == 1  # 00:30 period lacked forecast
        assert summary["rawForecastRevisionsCount"] == 6
        assert summary["eligibleForecastsCount"] == 3
        assert summary["decisionCutoffRule"] == "Day-Ahead (D-1 at 12:00 UTC)"

        metrics = payload["metrics"]
        assert metrics["sampleCount"] == 3
        assert metrics["unit"] == "MW"
        assert "maeMW" in metrics
        assert "rmseMW" in metrics
        assert "biasMW" in metrics

        # Verify matched data contains error calculations
        matched = payload["matchedData"]
        assert len(matched) == 3
        assert matched[0]["actualGenerationMW"] == 12000.0
        assert matched[0]["forecastGenerationMW"] == 11800.0
        assert matched[0]["errorMW"] == -200.0

    def test_evaluation_exclude_timeseries(self, test_client: TestClient, mock_client_dependency):
        """When include_timeseries=false is requested, matchedData must be empty."""
        response = test_client.get(
            "/api/v1/wind/evaluation?from_date=2026-01-01&to_date=2026-01-02&include_timeseries=false"
        )
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["matchedData"]) == 0
        assert payload["metrics"]["sampleCount"] == 3

    def test_custom_cutoff_hour_applied(self, test_client: TestClient, mock_client_dependency):
        """Supplying cutoff_hour=17 should reflect in summary."""
        response = test_client.get(
            "/api/v1/wind/evaluation?from_date=2026-01-01&to_date=2026-01-02&cutoff_hour=17"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["decisionCutoffRule"] == "Day-Ahead (D-1 at 17:00 UTC)"


class TestValidationAndErrorHandling:
    """Tests for input validation and error responses."""

    def test_invalid_date_order_returns_400(self, test_client: TestClient, mock_client_dependency):
        """from_date after to_date must return HTTP 400."""
        response = test_client.get("/api/v1/wind/evaluation?from_date=2026-01-10&to_date=2026-01-05")
        assert response.status_code == 400
        assert "from_date" in response.json()["detail"]

    def test_invalid_date_format_returns_422(self, test_client: TestClient, mock_client_dependency):
        """Malformed date string must return HTTP 422 validation error."""
        response = test_client.get("/api/v1/wind/evaluation?from_date=not-a-date&to_date=2026-01-31")
        assert response.status_code == 422

    def test_invalid_cutoff_hour_returns_422(self, test_client: TestClient, mock_client_dependency):
        """Cutoff hour > 23 must fail Pydantic validation."""
        response = test_client.get("/api/v1/wind/evaluation?cutoff_hour=25")
        assert response.status_code == 422

    def test_elexon_api_error_returns_502(self, test_client: TestClient):
        """When ElexonClient raises ElexonAPIError, endpoint must return HTTP 502."""
        mock_client = AsyncMock(spec=ElexonClient)
        mock_client.fetch_actual_wind_generation.side_effect = ElexonAPIError("Elexon upstream 503 unavailable")

        app.dependency_overrides[get_elexon_client] = lambda: mock_client
        try:
            response = test_client.get("/api/v1/wind/actuals?from_date=2026-01-01&to_date=2026-01-02")
            assert response.status_code == 502
            assert "Elexon upstream 503 unavailable" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
