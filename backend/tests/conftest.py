"""Pytest fixtures for backend tests."""

from datetime import datetime, timezone
from typing import List
import pytest
from fastapi.testclient import TestClient

from app.clients.elexon_client import ElexonClient
from app.config import Settings
from app.main import app
from app.models.schemas import WindActualRecord, WindForecastRecord
from app.services.forecast_service import ForecastService


@pytest.fixture
def test_settings() -> Settings:
    """Return test settings with deterministic parameters."""
    return Settings(
        APP_NAME="WindPulse Wind Forecast Evaluation API (Test)",
        APP_ENV="test",
        DAY_AHEAD_DECISION_CUTOFF_HOUR=12,
        ALLOWED_ORIGINS="http://localhost:3000",
    )


@pytest.fixture
def forecast_service(test_settings: Settings) -> ForecastService:
    """Return a ForecastService instance configured with test settings."""
    return ForecastService(settings=test_settings)


@pytest.fixture
def sample_actuals() -> List[WindActualRecord]:
    """Sample actual wind generation records for Jan 1 and Jan 2, 2026."""
    return [
        # Jan 1, 2026
        WindActualRecord(
            startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            generation=12000.0,
            settlementDate="2026-01-01",
            settlementPeriod=1,
            fuelType="WIND",
        ),
        WindActualRecord(
            startTime=datetime(2026, 1, 1, 0, 30, tzinfo=timezone.utc),
            generation=12200.0,
            settlementDate="2026-01-01",
            settlementPeriod=2,
            fuelType="WIND",
        ),
        WindActualRecord(
            startTime=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
            generation=11500.0,
            settlementDate="2026-01-01",
            settlementPeriod=3,
            fuelType="WIND",
        ),
        # Jan 2, 2026
        WindActualRecord(
            startTime=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
            generation=14000.0,
            settlementDate="2026-01-02",
            settlementPeriod=1,
            fuelType="WIND",
        ),
    ]


@pytest.fixture
def sample_forecasts() -> List[WindForecastRecord]:
    """Sample wind forecasts with varying publication times.

    Includes:
    - Pre-cutoff forecasts (eligible)
    - Post-cutoff forecasts (must be excluded to prevent leakage)
    - Earlier pre-cutoff forecasts (superseded by later pre-cutoff forecast)
    """
    return [
        # Target: 2026-01-01 00:00 UTC (Cutoff: 2025-12-31 12:00 UTC)
        # 1. Published early on 2025-12-30 (eligible, but superseded)
        WindForecastRecord(
            startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            publishTime=datetime(2025, 12, 30, 10, 0, tzinfo=timezone.utc),
            generation=10000.0,
        ),
        # 2. Published 2025-12-31 11:30 UTC (eligible, latest before 12:00 cutoff -> MUST BE CHOSEN)
        WindForecastRecord(
            startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            publishTime=datetime(2025, 12, 31, 11, 30, tzinfo=timezone.utc),
            generation=11800.0,
        ),
        # 3. Published 2025-12-31 14:00 UTC (POST-CUTOFF -> MUST BE EXCLUDED!)
        WindForecastRecord(
            startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            publishTime=datetime(2025, 12, 31, 14, 0, tzinfo=timezone.utc),
            generation=12050.0,
        ),
        # 4. Published on delivery day 2026-01-01 01:00 UTC (POST-CUTOFF -> MUST BE EXCLUDED!)
        WindForecastRecord(
            startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            publishTime=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
            generation=12100.0,
        ),

        # Target: 2026-01-01 01:00 UTC (Cutoff: 2025-12-31 12:00 UTC)
        # Single eligible forecast
        WindForecastRecord(
            startTime=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
            publishTime=datetime(2025, 12, 31, 11, 0, tzinfo=timezone.utc),
            generation=11000.0,
        ),

        # Target: 2026-01-02 00:00 UTC (Cutoff: 2026-01-01 12:00 UTC)
        # Eligible forecast
        WindForecastRecord(
            startTime=datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc),
            publishTime=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            generation=13500.0,
        ),
    ]


@pytest.fixture
def test_client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)
