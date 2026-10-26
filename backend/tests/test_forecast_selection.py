"""Unit tests for forecast selection, cutoff calculation, data leakage prevention, and matching."""

from datetime import datetime, timezone
from typing import List
import pytest

from app.models.schemas import WindActualRecord, WindForecastRecord
from app.services.forecast_service import ForecastService, calculate_day_ahead_cutoff


class TestCutoffCalculation:
    """Tests for day-ahead decision cutoff calculation."""

    def test_default_day_ahead_cutoff(self):
        """For target delivery on 2026-01-15 14:30 UTC, cutoff must be 2026-01-14 12:00 UTC."""
        target = datetime(2026, 1, 15, 14, 30, tzinfo=timezone.utc)
        cutoff = calculate_day_ahead_cutoff(target, cutoff_hour=12)

        expected = datetime(2026, 1, 14, 12, 0, 0, tzinfo=timezone.utc)
        assert cutoff == expected

    def test_custom_cutoff_hour(self):
        """Configuring cutoff_hour=17 should place cutoff at 17:00 UTC on D-1."""
        target = datetime(2026, 1, 20, 0, 0, tzinfo=timezone.utc)
        cutoff = calculate_day_ahead_cutoff(target, cutoff_hour=17)

        expected = datetime(2026, 1, 19, 17, 0, 0, tzinfo=timezone.utc)
        assert cutoff == expected

    def test_naive_datetime_converted_to_utc(self):
        """A naive datetime should be assumed UTC and produce a valid UTC cutoff."""
        naive_target = datetime(2026, 1, 5, 8, 0)
        cutoff = calculate_day_ahead_cutoff(naive_target, cutoff_hour=12)

        expected = datetime(2026, 1, 4, 12, 0, 0, tzinfo=timezone.utc)
        assert cutoff == expected
        assert cutoff.tzinfo == timezone.utc


class TestForecastSelectionAndLeakagePrevention:
    """Tests proving that forecast selection strictly prevents data leakage."""

    def test_selects_latest_forecast_before_cutoff(
        self,
        forecast_service: ForecastService,
        sample_forecasts: List[WindForecastRecord],
    ):
        """For target 2026-01-01 00:00, must choose the 11:30 forecast, not the 10:00 or post-cutoff ones."""
        selected = forecast_service.select_day_ahead_forecasts(sample_forecasts, cutoff_hour=12)

        target = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        assert target in selected

        chosen = selected[target]
        # Should pick generation=11800.0 (published 2025-12-31 11:30:00 UTC)
        assert chosen.generation == 11800.0
        assert chosen.publishTime == datetime(2025, 12, 31, 11, 30, tzinfo=timezone.utc)

    def test_strictly_excludes_forecast_published_after_cutoff(
        self,
        forecast_service: ForecastService,
    ):
        """Prove that a forecast published even 1 minute after the cutoff is strictly excluded."""
        target = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
        # Cutoff is 2026-01-09 12:00:00 UTC

        forecasts = [
            # Published at 12:01 UTC (1 minute after cutoff)
            WindForecastRecord(
                startTime=target,
                publishTime=datetime(2026, 1, 9, 12, 1, tzinfo=timezone.utc),
                generation=15000.0,
            ),
            # Published intra-day on delivery day
            WindForecastRecord(
                startTime=target,
                publishTime=datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc),
                generation=16000.0,
            ),
        ]

        selected = forecast_service.select_day_ahead_forecasts(forecasts, cutoff_hour=12)
        # Neither forecast is eligible; target must NOT be present in selected
        assert target not in selected

    def test_forecast_published_exactly_at_cutoff_is_eligible(
        self,
        forecast_service: ForecastService,
    ):
        """A forecast published exactly at the cutoff (12:00:00 UTC) is eligible."""
        target = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
        forecasts = [
            WindForecastRecord(
                startTime=target,
                publishTime=datetime(2026, 1, 9, 12, 0, 0, tzinfo=timezone.utc),
                generation=14500.0,
            )
        ]

        selected = forecast_service.select_day_ahead_forecasts(forecasts, cutoff_hour=12)
        assert target in selected
        assert selected[target].generation == 14500.0

    def test_handles_duplicate_forecast_records(
        self,
        forecast_service: ForecastService,
    ):
        """If identical duplicate forecasts exist for the same target time, selection works cleanly."""
        target = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
        pub_time = datetime(2026, 1, 9, 11, 0, tzinfo=timezone.utc)

        forecasts = [
            WindForecastRecord(startTime=target, publishTime=pub_time, generation=9000.0),
            WindForecastRecord(startTime=target, publishTime=pub_time, generation=9000.0),
        ]

        selected = forecast_service.select_day_ahead_forecasts(forecasts, cutoff_hour=12)
        assert target in selected
        assert selected[target].generation == 9000.0


class TestMatchingAndMissingData:
    """Tests for matching actuals and forecasts, coverage calculation, and accounting for missing data."""

    def test_matching_with_unmatched_half_hourly_actuals(
        self,
        forecast_service: ForecastService,
        sample_actuals: List[WindActualRecord],
        sample_forecasts: List[WindForecastRecord],
    ):
        """Test matching logic:
        - 2026-01-01 00:00: matches (actual=12000, forecast=11800)
        - 2026-01-01 00:30: half-hourly actual -> unmatched because WINDFOR has no :30 forecasts!
        - 2026-01-01 01:00: matches (actual=11500, forecast=11000)
        - 2026-01-02 00:00: matches (actual=14000, forecast=13500)
        """
        matched, missing_fc_count, missing_act_count, unmatched_half_hourly = (
            forecast_service.match_forecasts_and_actuals(
                actuals=sample_actuals,
                forecasts=sample_forecasts,
                cutoff_hour=12,
            )
        )

        assert len(matched) == 3
        # The 00:30 settlement period is counted as an unmatched half-hourly actual
        assert unmatched_half_hourly == 1
        # For the 3 hourly targets present in actuals and forecasts, all matched
        assert missing_fc_count == 0
        assert missing_act_count == 0

        # Verify matched record 1
        m1 = matched[0]
        assert m1.startTime == datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        assert m1.actualGenerationMW == 12000.0
        assert m1.forecastGenerationMW == 11800.0
        # Error = Forecast - Actual = 11800 - 12000 = -200 MW (under-forecast)
        assert m1.errorMW == -200.0
        assert m1.absoluteErrorMW == 200.0
        # Percentage error = (200 / 12000) * 100 = 1.67%
        assert m1.percentageError == pytest.approx(1.67, abs=0.01)

    def test_full_evaluation_summary(
        self,
        forecast_service: ForecastService,
        sample_actuals: List[WindActualRecord],
        sample_forecasts: List[WindForecastRecord],
    ):
        """Test the evaluate() method returns correct summary fields and coverage."""
        response = forecast_service.evaluate(
            actuals=sample_actuals,
            forecasts=sample_forecasts,
            from_date="2026-01-01",
            to_date="2026-01-02",
            cutoff_hour=12,
        )

        assert response.status == "success"
        # 2 days * 24 hours = 48 expected hourly forecast targets
        assert response.summary.totalExpectedHourlyPeriods == 48
        assert response.summary.totalExpectedPeriods == 48
        # 2 days * 48 half-hours = 96 expected settlement periods
        assert response.summary.totalActualHalfHourlyPeriods == 96
        assert response.summary.actualRecordsCount == len(sample_actuals)

        # Raw publication revisions count
        assert response.summary.rawForecastRevisionsCount == len(sample_forecasts)
        # Unique target hours having an eligible day-ahead forecast
        assert response.summary.eligibleForecastsCount == 3

        # Matched and unmatched breakdown
        assert response.summary.matchedCount == 3
        assert response.summary.unmatchedHalfHourlyActualsCount == 1
        # 48 expected hours - 3 matched hours = 45 hours lacking forecasts in sample
        assert response.summary.missingHourlyForecastCount == 45
        assert response.summary.missingForecastCount == 45
        assert response.summary.coveragePercentage == pytest.approx(6.25, abs=0.01)

        # Check metrics computed over the 3 matched hourly periods
        assert response.metrics.sampleCount == 3
        assert response.metrics.unit == "MW"
        assert response.metrics.maeMW > 0

    def test_complete_hourly_coverage_reaches_100_percent(
        self,
        forecast_service: ForecastService,
    ):
        """When every expected hourly period has both actual and eligible forecast, coverage is exactly 100%."""
        # 1 day evaluation (2026-01-01): 24 hours
        actuals = [
            WindActualRecord(
                startTime=datetime(2026, 1, 1, h, 0, tzinfo=timezone.utc),
                generation=10000.0 + h * 100,
                settlementDate="2026-01-01",
                settlementPeriod=h * 2 + 1,
            )
            for h in range(24)
        ]
        # Include 24 half-hourly actuals as well
        actuals += [
            WindActualRecord(
                startTime=datetime(2026, 1, 1, h, 30, tzinfo=timezone.utc),
                generation=10050.0 + h * 100,
                settlementDate="2026-01-01",
                settlementPeriod=h * 2 + 2,
            )
            for h in range(24)
        ]

        # 24 eligible day-ahead forecasts (published 2025-12-31 11:00 UTC)
        forecasts = [
            WindForecastRecord(
                startTime=datetime(2026, 1, 1, h, 0, tzinfo=timezone.utc),
                publishTime=datetime(2025, 12, 31, 11, 0, tzinfo=timezone.utc),
                generation=10100.0 + h * 100,
            )
            for h in range(24)
        ]

        response = forecast_service.evaluate(
            actuals=actuals,
            forecasts=forecasts,
            from_date="2026-01-01",
            to_date="2026-01-01",
            cutoff_hour=12,
        )

        assert response.summary.totalExpectedHourlyPeriods == 24
        assert response.summary.totalActualHalfHourlyPeriods == 48
        assert response.summary.matchedCount == 24
        assert response.summary.missingHourlyForecastCount == 0
        assert response.summary.unmatchedHalfHourlyActualsCount == 24
        # Every hourly forecast target was matched -> exactly 100% coverage
        assert response.summary.coveragePercentage == 100.0

    def test_missing_hourly_forecast_reduces_coverage(
        self,
        forecast_service: ForecastService,
    ):
        """Missing an hourly forecast must visibly reduce coverage below 100%."""
        # 1 day evaluation (24 hours), but only 23 forecasts provided (hour 12 missing)
        actuals = [
            WindActualRecord(
                startTime=datetime(2026, 1, 1, h, 0, tzinfo=timezone.utc),
                generation=10000.0,
                settlementDate="2026-01-01",
                settlementPeriod=h * 2 + 1,
            )
            for h in range(24)
        ]

        forecasts = [
            WindForecastRecord(
                startTime=datetime(2026, 1, 1, h, 0, tzinfo=timezone.utc),
                publishTime=datetime(2025, 12, 31, 11, 0, tzinfo=timezone.utc),
                generation=10000.0,
            )
            for h in range(24)
            if h != 12  # Hour 12 is missing
        ]

        response = forecast_service.evaluate(
            actuals=actuals,
            forecasts=forecasts,
            from_date="2026-01-01",
            to_date="2026-01-01",
            cutoff_hour=12,
        )

        assert response.summary.totalExpectedHourlyPeriods == 24
        assert response.summary.matchedCount == 23
        assert response.summary.missingHourlyForecastCount == 1
        assert response.summary.coveragePercentage == pytest.approx(95.83, abs=0.01)
