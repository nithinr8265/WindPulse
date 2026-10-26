"""Pydantic schemas for data validation and API response formatting."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------------------
# Raw Data Record Models (Elexon BMRS format)
# -------------------------------------------------------------------------

class WindActualRecord(BaseModel):
    """Represents a single half-hourly actual wind generation record from Elexon FUELHH."""
    startTime: datetime = Field(..., description="Start of the half-hour settlement period in UTC")
    generation: float = Field(..., description="Actual wind power generated in Megawatts (MW)")
    fuelType: str = Field(default="WIND", description="Generation fuel type, filtered to WIND")
    settlementDate: Optional[str] = Field(default=None, description="Settlement calendar date (YYYY-MM-DD)")
    settlementPeriod: Optional[int] = Field(default=None, description="Settlement period number (1-48/50)")


class WindForecastRecord(BaseModel):
    """Represents a single wind generation forecast record from Elexon WINDFOR."""
    startTime: datetime = Field(..., description="Target settlement half-hour start time in UTC")
    publishTime: datetime = Field(..., description="Timestamp when the forecast was issued/published in UTC")
    generation: float = Field(..., description="Forecasted wind generation in Megawatts (MW)")
    dataset: Optional[str] = Field(default="WINDFOR", description="Elexon dataset name")


# -------------------------------------------------------------------------
# Evaluation Models
# -------------------------------------------------------------------------

class MatchedRecord(BaseModel):
    """A matched pair of actual wind generation and eligible day-ahead forecast for a target time."""
    startTime: datetime = Field(..., description="Target delivery half-hour start time (UTC)")
    targetDate: str = Field(..., description="Calendar date of delivery (YYYY-MM-DD)")
    settlementPeriod: Optional[int] = Field(default=None, description="Half-hour settlement period (1-48)")
    actualGenerationMW: float = Field(..., description="Actual wind generation (MW)")
    forecastGenerationMW: float = Field(..., description="Selected eligible forecast wind generation (MW)")
    forecastPublishTime: datetime = Field(..., description="Publication timestamp of the selected forecast (UTC)")
    decisionCutoffTime: datetime = Field(..., description="Day-ahead decision cutoff deadline (UTC)")
    errorMW: float = Field(
        ...,
        description="Forecast error in MW: (Forecast - Actual). Positive means over-forecast; negative means under-forecast.",
    )
    absoluteErrorMW: float = Field(
        ...,
        description="Absolute forecast error in MW: |Forecast - Actual|",
    )
    percentageError: Optional[float] = Field(
        default=None,
        description="Absolute percentage error: (|Forecast - Actual| / Actual) * 100 where Actual > 0",
    )


class AccuracyMetrics(BaseModel):
    """Quantitative accuracy metrics computed over matched forecast and actual pairs."""
    sampleCount: int = Field(..., description="Number of matched observations evaluated")
    maeMW: float = Field(
        ...,
        description="Mean Absolute Error (MW): Average magnitude of errors regardless of direction",
    )
    rmseMW: float = Field(
        ...,
        description="Root Mean Squared Error (MW): Penalizes larger forecast errors more heavily",
    )
    biasMW: float = Field(
        ...,
        description="Mean Error / Bias (MW): Average signed error (Forecast - Actual). Positive indicates systematic over-forecasting.",
    )
    nmaePercentage: Optional[float] = Field(
        default=None,
        description="Normalized MAE (%): MAE divided by mean actual generation, expressed as a percentage",
    )
    mapePercentage: Optional[float] = Field(
        default=None,
        description="Mean Absolute Percentage Error (%): Mean of absolute percentage errors where actual > 0",
    )
    meanActualMW: float = Field(..., description="Average actual generation across all matched periods (MW)")
    meanForecastMW: float = Field(..., description="Average forecast generation across all matched periods (MW)")
    unit: str = Field(default="MW", description="Standard measurement unit for power generation")
    definitions: Dict[str, str] = Field(
        default_factory=lambda: {
            "errorMW": "Forecast - Actual generation in Megawatts (MW)",
            "maeMW": "Mean Absolute Error: (1/N) * sum(|Forecast - Actual|)",
            "rmseMW": "Root Mean Squared Error: sqrt((1/N) * sum((Forecast - Actual)^2))",
            "biasMW": "Forecast Bias (Mean Error): (1/N) * sum(Forecast - Actual). >0 = over-forecast, <0 = under-forecast",
            "nmaePercentage": "Normalized MAE: (MAE / Mean(Actual)) * 100%",
            "mapePercentage": "MAPE: Mean(|Forecast - Actual| / Actual) * 100% for actual > 0",
        },
        description="Human-readable definitions and formulas for all metrics",
    )


class EvaluationSummary(BaseModel):
    """Summary of data coverage, forecast resolution, and matching completeness."""
    targetPeriodStart: datetime = Field(..., description="Start of evaluation window (UTC)")
    targetPeriodEnd: datetime = Field(..., description="End of evaluation window (UTC)")
    decisionCutoffRule: str = Field(
        ...,
        description="Rule defining the day-ahead purchasing decision deadline",
    )

    # Granular resolution and record breakdown
    totalExpectedHourlyPeriods: int = Field(
        ...,
        description="Total expected hourly forecast target periods in the evaluation window (24 per day)",
    )
    totalActualHalfHourlyPeriods: int = Field(
        ...,
        description="Total actual half-hourly settlement periods in the evaluation window (48 per day)",
    )
    rawForecastRevisionsCount: int = Field(
        ...,
        description="Total raw forecast publication revisions retrieved targeting the evaluation window",
    )
    eligibleForecastsCount: int = Field(
        ...,
        description="Count of unique target delivery hours having an eligible forecast published prior to cutoff",
    )
    matchedCount: int = Field(
        ...,
        description="Number of target hours successfully matched with both actual generation and eligible day-ahead forecast",
    )
    missingHourlyForecastCount: int = Field(
        ...,
        description="Number of expected hourly target periods lacking an eligible day-ahead forecast",
    )
    missingHourlyActualCount: int = Field(
        ...,
        description="Number of expected hourly target periods lacking actual generation data at :00",
    )
    unmatchedHalfHourlyActualsCount: int = Field(
        ...,
        description="Number of half-hourly actual settlement periods (:30) for which no WINDFOR forecast is published",
    )
    coveragePercentage: float = Field(
        ...,
        description="Matched hourly periods as a percentage of total expected hourly forecast target periods",
    )

    # Compatibility aliases
    totalExpectedPeriods: int = Field(
        ...,
        description="Alias for totalExpectedHourlyPeriods (the forecast evaluation resolution)",
    )
    actualRecordsCount: int = Field(
        ...,
        description="Total actual records retrieved (half-hourly FUELHH records)",
    )
    forecastRecordsCount: int = Field(
        ...,
        description="Total raw forecast publication revisions retrieved",
    )
    missingForecastCount: int = Field(
        ...,
        description="Alias for missingHourlyForecastCount (expected hourly periods lacking an eligible forecast)",
    )
    missingActualCount: int = Field(
        ...,
        description="Alias for missingHourlyActualCount (expected hourly periods lacking actual generation data)",
    )


# -------------------------------------------------------------------------
# API Response Wrappers
# -------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health check endpoint response schema."""
    status: str = Field(default="ok", description="Service status")
    app_name: str = Field(..., description="Application name")
    timestamp: datetime = Field(..., description="Current server time (UTC)")
    environment: str = Field(..., description="Application environment")


class ActualsResponse(BaseModel):
    """Response containing actual wind generation records."""
    status: str = Field(default="success")
    count: int = Field(..., description="Number of returned actual records")
    fromDate: str = Field(..., description="Start date filter (YYYY-MM-DD)")
    toDate: str = Field(..., description="End date filter (YYYY-MM-DD)")
    data: List[WindActualRecord] = Field(..., description="List of actual wind generation records")


class ForecastsResponse(BaseModel):
    """Response containing raw wind forecast records."""
    status: str = Field(default="success")
    count: int = Field(..., description="Number of returned forecast records")
    fromDate: str = Field(..., description="Start date filter (YYYY-MM-DD)")
    toDate: str = Field(..., description="End date filter (YYYY-MM-DD)")
    data: List[WindForecastRecord] = Field(..., description="List of wind forecast records")


class EvaluationResponse(BaseModel):
    """Full evaluation response with summary, quantitative accuracy metrics, and matched timeseries."""
    status: str = Field(default="success")
    summary: EvaluationSummary = Field(..., description="Dataset coverage and matching breakdown")
    metrics: AccuracyMetrics = Field(..., description="Calculated quantitative accuracy metrics")
    matchedData: List[MatchedRecord] = Field(..., description="Detailed time-series of matched records")
