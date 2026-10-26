"""FastAPI routes for wind generation actuals, forecasts, and day-ahead evaluation."""

from datetime import date, datetime, timezone
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.clients.elexon_client import ElexonAPIError, ElexonClient
from app.config import Settings, get_settings
from app.models.schemas import (
    ActualsResponse,
    EvaluationResponse,
    ForecastsResponse,
    HealthResponse,
)
from app.services.forecast_service import ForecastService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_elexon_client(settings: Settings = Depends(get_settings)) -> ElexonClient:
    """Dependency provider for ElexonClient."""
    return ElexonClient(settings=settings)


def get_forecast_service(settings: Settings = Depends(get_settings)) -> ForecastService:
    """Dependency provider for ForecastService."""
    return ForecastService(settings=settings)


def validate_date_range(from_date: str, to_date: str) -> None:
    """Validate ISO date format (YYYY-MM-DD) and check that from_date <= to_date."""
    try:
        d_from = date.fromisoformat(from_date)
        d_to = date.fromisoformat(to_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Expected YYYY-MM-DD (e.g. 2026-01-01): {str(exc)}",
        )

    if d_from > d_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"from_date ({from_date}) must be before or equal to to_date ({to_date})",
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Backend Health Check",
    description="Returns service status, environment, and server UTC timestamp.",
    tags=["Health"],
)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Check backend operational status."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        timestamp=datetime.now(timezone.utc),
        environment=settings.APP_ENV,
    )


@router.get(
    "/api/v1/wind/actuals",
    response_model=ActualsResponse,
    summary="Get Actual Wind Generation",
    description="Retrieve actual half-hourly wind generation records from Elexon BMRS FUELHH for January 2026.",
    tags=["Wind Generation"],
)
async def get_actuals(
    from_date: str = Query(
        default="2026-01-01",
        description="Settlement start date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    to_date: str = Query(
        default="2026-01-31",
        description="Settlement end date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        description="Optional limit on returned records count",
    ),
    client: ElexonClient = Depends(get_elexon_client),
) -> ActualsResponse:
    """Retrieve actual half-hourly wind generation data filtered to fuelType=WIND."""
    validate_date_range(from_date, to_date)

    try:
        actuals = await client.fetch_actual_wind_generation(from_date=from_date, to_date=to_date)
        if limit is not None:
            actuals = actuals[:limit]

        return ActualsResponse(
            status="success",
            count=len(actuals),
            fromDate=from_date,
            toDate=to_date,
            data=actuals,
        )
    except ElexonAPIError as exc:
        logger.error("Failed to retrieve actual wind data: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error querying Elexon FUELHH: {str(exc)}",
        )


@router.get(
    "/api/v1/wind/forecasts",
    response_model=ForecastsResponse,
    summary="Get Wind Generation Forecasts",
    description="Retrieve raw wind forecasts from Elexon BMRS WINDFOR targeting January 2026 delivery times.",
    tags=["Wind Generation"],
)
async def get_forecasts(
    from_date: str = Query(
        default="2026-01-01",
        description="Target start delivery date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    to_date: str = Query(
        default="2026-01-31",
        description="Target end delivery date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    limit: Optional[int] = Query(
        default=None,
        ge=1,
        description="Optional limit on returned records count",
    ),
    client: ElexonClient = Depends(get_elexon_client),
) -> ForecastsResponse:
    """Retrieve raw wind generation forecasts with publication and target delivery timestamps."""
    validate_date_range(from_date, to_date)

    try:
        forecasts = await client.fetch_wind_forecasts(from_date=from_date, to_date=to_date)
        if limit is not None:
            forecasts = forecasts[:limit]

        return ForecastsResponse(
            status="success",
            count=len(forecasts),
            fromDate=from_date,
            toDate=to_date,
            data=forecasts,
        )
    except ElexonAPIError as exc:
        logger.error("Failed to retrieve wind forecasts: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error querying Elexon WINDFOR: {str(exc)}",
        )


@router.get(
    "/api/v1/wind/evaluation",
    response_model=EvaluationResponse,
    summary="Evaluate Day-Ahead Forecast Accuracy",
    description=(
        "Evaluates day-ahead wind generation forecasts against actuals for January 2026. "
        "Selects the latest eligible forecast published before the day-ahead purchasing cutoff "
        "(D-1 at configured cutoff hour UTC) to strictly avoid data leakage. "
        "Calculates quantitative accuracy metrics including MAE, RMSE, and Bias (in MW)."
    ),
    tags=["Evaluation"],
)
async def evaluate_forecasts(
    from_date: str = Query(
        default="2026-01-01",
        description="Evaluation start date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    to_date: str = Query(
        default="2026-01-31",
        description="Evaluation end date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    cutoff_hour: Optional[int] = Query(
        default=None,
        ge=0,
        le=23,
        description="Day-ahead cutoff hour on D-1 (0-23 UTC; default from config: 12 UTC)",
    ),
    include_timeseries: bool = Query(
        default=True,
        description="Include full matched time-series data or return summary and metrics only",
    ),
    client: ElexonClient = Depends(get_elexon_client),
    service: ForecastService = Depends(get_forecast_service),
) -> EvaluationResponse:
    """Run full day-ahead forecast evaluation and compute quantitative accuracy metrics."""
    validate_date_range(from_date, to_date)

    try:
        # Retrieve actuals and forecasts in parallel or sequence
        actuals = await client.fetch_actual_wind_generation(from_date=from_date, to_date=to_date)
        forecasts = await client.fetch_wind_forecasts(from_date=from_date, to_date=to_date)

        evaluation = service.evaluate(
            actuals=actuals,
            forecasts=forecasts,
            from_date=from_date,
            to_date=to_date,
            cutoff_hour=cutoff_hour,
        )

        if not include_timeseries:
            evaluation.matchedData = []

        return evaluation

    except ElexonAPIError as exc:
        logger.error("Failed to run forecast evaluation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"External data source error: {str(exc)}",
        )
