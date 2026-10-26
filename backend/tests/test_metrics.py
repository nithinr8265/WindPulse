"""Unit tests for quantitative accuracy metrics (MAE, RMSE, Bias, nMAE, MAPE)."""

from datetime import datetime, timezone
import pytest

from app.models.schemas import MatchedRecord
from app.services.metrics_service import MetricsService


def create_matched_record(actual: float, forecast: float) -> MatchedRecord:
    """Helper to create a minimal MatchedRecord for metric tests."""
    error = forecast - actual
    abs_error = abs(error)
    pct_error = (abs_error / actual * 100.0) if actual > 0 else None
    dt = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    return MatchedRecord(
        startTime=dt,
        targetDate="2026-01-01",
        settlementPeriod=1,
        actualGenerationMW=actual,
        forecastGenerationMW=forecast,
        forecastPublishTime=dt,
        decisionCutoffTime=dt,
        errorMW=error,
        absoluteErrorMW=abs_error,
        percentageError=pct_error,
    )


class TestMetricsCalculation:
    """Tests verifying quantitative accuracy metric calculations."""

    def test_hand_calculated_values(self):
        """Test accuracy metrics against precise hand-calculated expected values."""
        records = [
            create_matched_record(actual=100.0, forecast=110.0),  # err = +10, abs = 10, sq = 100, pct = 10%
            create_matched_record(actual=200.0, forecast=190.0),  # err = -10, abs = 10, sq = 100, pct = 5%
            create_matched_record(actual=300.0, forecast=320.0),  # err = +20, abs = 20, sq = 400, pct = 6.6667%
        ]

        metrics = MetricsService.calculate_metrics(records)

        assert metrics.sampleCount == 3
        # MAE = (10 + 10 + 20) / 3 = 13.33 MW
        assert metrics.maeMW == pytest.approx(13.33, abs=0.01)
        # RMSE = sqrt(600 / 3) = sqrt(200) = 14.14 MW
        assert metrics.rmseMW == pytest.approx(14.14, abs=0.01)
        # Bias = (10 - 10 + 20) / 3 = +6.67 MW (positive indicates over-forecast)
        assert metrics.biasMW == pytest.approx(6.67, abs=0.01)
        # Mean actual = 200.0 MW
        assert metrics.meanActualMW == 200.0
        # Mean forecast = 206.67 MW
        assert metrics.meanForecastMW == pytest.approx(206.67, abs=0.01)
        # nMAE = 13.333... / 200 * 100 = 6.67%
        assert metrics.nmaePercentage == pytest.approx(6.67, abs=0.01)
        # MAPE = (10 + 5 + 6.6667) / 3 = 7.22%
        assert metrics.mapePercentage == pytest.approx(7.22, abs=0.01)
        assert metrics.unit == "MW"
        assert "maeMW" in metrics.definitions

    def test_perfect_forecast(self):
        """When forecast perfectly matches actual, MAE, RMSE, and Bias must all equal 0."""
        records = [
            create_matched_record(actual=5000.0, forecast=5000.0),
            create_matched_record(actual=8000.0, forecast=8000.0),
        ]

        metrics = MetricsService.calculate_metrics(records)

        assert metrics.sampleCount == 2
        assert metrics.maeMW == 0.0
        assert metrics.rmseMW == 0.0
        assert metrics.biasMW == 0.0
        assert metrics.nmaePercentage == 0.0
        assert metrics.mapePercentage == 0.0

    def test_consistent_under_forecast_bias(self):
        """When forecast consistently under-predicts, Bias must be negative."""
        records = [
            create_matched_record(actual=1000.0, forecast=800.0),  # err = -200
            create_matched_record(actual=2000.0, forecast=1700.0),  # err = -300
        ]

        metrics = MetricsService.calculate_metrics(records)

        assert metrics.maeMW == 250.0
        assert metrics.biasMW == -250.0  # Negative indicates under-forecasting

    def test_empty_records_does_not_crash(self):
        """Calculating metrics for an empty list must not raise ZeroDivisionError."""
        metrics = MetricsService.calculate_metrics([])

        assert metrics.sampleCount == 0
        assert metrics.maeMW == 0.0
        assert metrics.rmseMW == 0.0
        assert metrics.biasMW == 0.0
        assert metrics.nmaePercentage is None
        assert metrics.mapePercentage is None

    def test_zero_actual_generation_handled_cleanly(self):
        """When actual generation is zero, percentage error avoids ZeroDivisionError."""
        records = [
            create_matched_record(actual=0.0, forecast=50.0),  # actual is 0
            create_matched_record(actual=100.0, forecast=120.0),
        ]

        metrics = MetricsService.calculate_metrics(records)

        assert metrics.sampleCount == 2
        assert metrics.maeMW == 35.0  # (50 + 20) / 2 = 35
        # MAPE should only calculate over non-zero actuals (record 2: 20%)
        assert metrics.mapePercentage == 20.0
