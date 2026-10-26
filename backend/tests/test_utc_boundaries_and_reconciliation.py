"""Automated test suite for UTC calendar boundary handling, UK DST transitions,
and actual-record count reconciliation invariants using controlled fixtures.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List
import pytest

from app.models.schemas import WindActualRecord, WindForecastRecord
from app.services.forecast_service import ForecastService


def _generate_day_actuals(
    day: date,
    offset_hours: int = 0,
    base_generation: float = 10000.0,
    include_half_hourly: bool = True,
) -> List[WindActualRecord]:
    """Helper to generate half-hourly or hourly actual records for a given date in UTC."""
    records: List[WindActualRecord] = []
    periods_per_hour = 2 if include_half_hourly else 1
    sp = 1
    for h in range(24):
        for m in (0, 30) if include_half_hourly else (0,):
            st = datetime.combine(day, time(h, m, tzinfo=timezone.utc))
            records.append(
                WindActualRecord(
                    startTime=st,
                    generation=base_generation + h * 50.0 + (25.0 if m == 30 else 0.0),
                    settlementDate=day.isoformat(),
                    settlementPeriod=sp,
                    fuelType="WIND",
                )
            )
            sp += 1
    return records


def _generate_day_forecasts(
    day: date,
    base_generation: float = 10500.0,
) -> List[WindForecastRecord]:
    """Helper to generate 24 hourly day-ahead forecasts published on D-1 at 11:00 UTC."""
    cutoff_publish_time = datetime.combine(
        day - timedelta(days=1), time(11, 0, tzinfo=timezone.utc)
    )
    return [
        WindForecastRecord(
            startTime=datetime.combine(day, time(h, 0, tzinfo=timezone.utc)),
            publishTime=cutoff_publish_time,
            generation=base_generation + h * 50.0,
            dataset="WINDFOR",
        )
        for h in range(24)
    ]


class TestNormalGmtDay:
    """Verifies evaluation and reconciliation on a normal GMT day (e.g. 15 January 2026)."""

    def test_normal_gmt_day_reconciliation(self, forecast_service: ForecastService):
        target_day = date(2026, 1, 15)
        actuals = _generate_day_actuals(target_day)
        forecasts = _generate_day_forecasts(target_day)

        assert len(actuals) == 48
        assert len(forecasts) == 24

        res = forecast_service.evaluate(
            actuals=actuals,
            forecasts=forecasts,
            from_date=target_day.isoformat(),
            to_date=target_day.isoformat(),
        )

        s = res.summary
        assert s.totalExpectedHourlyPeriods == 24
        assert s.totalActualHalfHourlyPeriods == 48
        assert s.actualRecordsCount == 48
        assert s.matchedCount == 24
        assert s.missingHourlyForecastCount == 0
        assert s.missingHourlyActualCount == 0
        assert s.unmatchedHalfHourlyActualsCount == 24
        assert s.coveragePercentage == 100.0

        # Invariant: Matched (24) + Unmatched :30 (24) == In-scope actuals (48)
        assert s.matchedCount + s.unmatchedHalfHourlyActualsCount == s.actualRecordsCount


class TestNormalBstDay:
    """Verifies evaluation and reconciliation on a normal BST day (e.g. 15 June 2026)."""

    def test_normal_bst_day_reconciliation(self, forecast_service: ForecastService):
        target_day = date(2026, 6, 15)
        actuals = _generate_day_actuals(target_day)
        forecasts = _generate_day_forecasts(target_day)

        res = forecast_service.evaluate(
            actuals=actuals,
            forecasts=forecasts,
            from_date=target_day.isoformat(),
            to_date=target_day.isoformat(),
        )

        s = res.summary
        assert s.totalExpectedHourlyPeriods == 24
        assert s.totalActualHalfHourlyPeriods == 48
        assert s.actualRecordsCount == 48
        assert s.matchedCount == 24
        assert s.unmatchedHalfHourlyActualsCount == 24
        assert s.coveragePercentage == 100.0
        assert s.matchedCount + s.unmatchedHalfHourlyActualsCount == s.actualRecordsCount


class TestAutumnDstTransition:
    """Verifies that on the UK autumn DST clock change (25 October 2026),
    records from 24 October do not leak, and exactly 48 half-hours are evaluated.
    """

    def test_autumn_dst_excludes_previous_day_bleed(self, forecast_service: ForecastService):
        target_day = date(2026, 10, 25)

        # Simulate the 50 settlement periods returned by Elexon for settlementDate=2026-10-25:
        # SP 1: 2026-10-24 23:00 UTC (from previous UTC day)
        # SP 2: 2026-10-24 23:30 UTC (from previous UTC day)
        # SP 3..50: 2026-10-25 00:00 to 23:30 UTC (48 records)
        bleed_sp1 = WindActualRecord(
            startTime=datetime(2026, 10, 24, 23, 0, tzinfo=timezone.utc),
            generation=13539.0,
            settlementDate="2026-10-25",
            settlementPeriod=1,
            fuelType="WIND",
        )
        bleed_sp2 = WindActualRecord(
            startTime=datetime(2026, 10, 24, 23, 30, tzinfo=timezone.utc),
            generation=13032.0,
            settlementDate="2026-10-25",
            settlementPeriod=2,
            fuelType="WIND",
        )

        in_window_actuals = _generate_day_actuals(target_day)
        # Combined raw records: 50 items
        raw_50_actuals = [bleed_sp1, bleed_sp2] + in_window_actuals
        assert len(raw_50_actuals) == 50

        forecasts = _generate_day_forecasts(target_day)

        res = forecast_service.evaluate(
            actuals=raw_50_actuals,
            forecasts=forecasts,
            from_date=target_day.isoformat(),
            to_date=target_day.isoformat(),
        )

        s = res.summary
        # Expected periods
        assert s.totalExpectedHourlyPeriods == 24
        assert s.totalActualHalfHourlyPeriods == 48

        # In-scope actual records retrieved must strictly equal 48 (not 50!)
        assert s.actualRecordsCount == 48

        # Matched hourly periods must be exactly 24
        assert s.matchedCount == 24
        assert s.missingHourlyForecastCount == 0
        assert s.missingHourlyActualCount == 0

        # Unmatched half-hourly actuals must be exactly 24 (not 25!)
        assert s.unmatchedHalfHourlyActualsCount == 24

        # 100% coverage
        assert s.coveragePercentage == 100.0

        # Invariant holds: 24 matched + 24 unmatched :30 == 48 in-scope actuals
        assert s.matchedCount + s.unmatchedHalfHourlyActualsCount == s.actualRecordsCount

        # Confirm that every matched record startTime is strictly in 2026-10-25
        for m in res.matchedData:
            assert m.startTime.date() == target_day
            assert m.startTime >= datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
            assert m.startTime <= datetime(2026, 10, 25, 23, 0, tzinfo=timezone.utc)


class TestSpringDstTransition:
    """Verifies that on the UK spring DST transition (e.g. 29 March 2026),
    the UTC evaluation window correctly handles the 24 UTC hours / 48 half-hours.
    """

    def test_spring_dst_utc_continuity(self, forecast_service: ForecastService):
        target_day = date(2026, 3, 29)
        actuals = _generate_day_actuals(target_day)
        forecasts = _generate_day_forecasts(target_day)

        res = forecast_service.evaluate(
            actuals=actuals,
            forecasts=forecasts,
            from_date=target_day.isoformat(),
            to_date=target_day.isoformat(),
        )

        s = res.summary
        assert s.totalExpectedHourlyPeriods == 24
        assert s.totalActualHalfHourlyPeriods == 48
        assert s.actualRecordsCount == 48
        assert s.matchedCount == 24
        assert s.unmatchedHalfHourlyActualsCount == 24
        assert s.coveragePercentage == 100.0
        assert s.matchedCount + s.unmatchedHalfHourlyActualsCount == s.actualRecordsCount


class TestUtcBoundaryEdgeCases:
    """Verifies that actual records immediately before, at start, at end, and after
    the requested interval [start_utc, end_utc) are correctly accepted or rejected.
    """

    def test_strict_interval_filtering(self, forecast_service: ForecastService):
        target_day = date(2026, 10, 25)

        # Edges around [2026-10-25 00:00:00Z, 2026-10-26 00:00:00Z)
        t_before = datetime(2026, 10, 24, 23, 30, tzinfo=timezone.utc)
        t_first = datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc)
        t_last = datetime(2026, 10, 25, 23, 30, tzinfo=timezone.utc)
        t_end = datetime(2026, 10, 26, 0, 0, tzinfo=timezone.utc)      # exactly at end bound -> must reject
        t_after = datetime(2026, 10, 26, 0, 30, tzinfo=timezone.utc)

        test_records = [
            WindActualRecord(startTime=t_before, generation=100.0, settlementDate="2026-10-25", settlementPeriod=2),
            WindActualRecord(startTime=t_first, generation=200.0, settlementDate="2026-10-25", settlementPeriod=3),
            WindActualRecord(startTime=t_last, generation=300.0, settlementDate="2026-10-25", settlementPeriod=50),
            WindActualRecord(startTime=t_end, generation=400.0, settlementDate="2026-10-26", settlementPeriod=1),
            WindActualRecord(startTime=t_after, generation=500.0, settlementDate="2026-10-26", settlementPeriod=2),
        ]

        forecasts = [
            WindForecastRecord(
                startTime=t_first,
                publishTime=datetime(2026, 10, 24, 11, 0, tzinfo=timezone.utc),
                generation=210.0,
            )
        ]

        res = forecast_service.evaluate(
            actuals=test_records,
            forecasts=forecasts,
            from_date=target_day.isoformat(),
            to_date=target_day.isoformat(),
        )

        # Only t_first and t_last are within [2026-10-25 00:00:00Z, 2026-10-26 00:00:00Z)
        assert res.summary.actualRecordsCount == 2
        assert res.summary.matchedCount == 1  # t_first matched
        assert res.summary.unmatchedHalfHourlyActualsCount == 1  # t_last is :30
        assert res.summary.matchedCount + res.summary.unmatchedHalfHourlyActualsCount == 2


class TestIncompleteDayHandling:
    """Verifies that an incomplete current day (e.g. 26 October at midday)
    correctly classifies missing future periods and preserves 50% coverage.
    """

    def test_midday_incomplete_day(self, forecast_service: ForecastService):
        target_day = date(2026, 10, 26)

        # Only the first 12 hours (00:00 to 11:30 UTC) exist
        elapsed_actuals: List[WindActualRecord] = []
        for h in range(12):
            for m in (0, 30):
                elapsed_actuals.append(
                    WindActualRecord(
                        startTime=datetime.combine(target_day, time(h, m, tzinfo=timezone.utc)),
                        generation=12000.0 + h * 100,
                        settlementDate=target_day.isoformat(),
                        settlementPeriod=h * 2 + (1 if m == 0 else 2),
                    )
                )

        assert len(elapsed_actuals) == 24  # 12 hours * 2 = 24 half-hours

        # Forecasts exist for all 24 hours of the day (published day-ahead)
        forecasts = _generate_day_forecasts(target_day)

        res = forecast_service.evaluate(
            actuals=elapsed_actuals,
            forecasts=forecasts,
            from_date=target_day.isoformat(),
            to_date=target_day.isoformat(),
        )

        s = res.summary
        assert s.totalExpectedHourlyPeriods == 24
        assert s.totalActualHalfHourlyPeriods == 48
        assert s.eligibleForecastsCount == 24
        assert s.actualRecordsCount == 24
        assert s.matchedCount == 12
        assert s.missingHourlyForecastCount == 0
        assert s.missingHourlyActualCount == 12  # Future 12 hours lack actuals
        assert s.unmatchedHalfHourlyActualsCount == 12  # Elapsed 12 half-hours
        assert s.coveragePercentage == 50.0

        # Invariant holds for the elapsed records: 12 matched + 12 unmatched :30 == 24 actuals
        assert s.matchedCount + s.unmatchedHalfHourlyActualsCount == s.actualRecordsCount


class TestMissingForecastAccounting:
    """Verifies exact invariant when an expected hourly target has an actual record
    but lacks an eligible day-ahead forecast.
    """

    def test_hourly_actual_lacking_forecast_is_accounted_for(self, forecast_service: ForecastService):
        target_day = date(2026, 1, 10)
        actuals = _generate_day_actuals(target_day)  # 24 :00 and 24 :30 = 48 records

        # Only 20 forecasts are provided (hours 20..23 missing)
        forecasts = [
            WindForecastRecord(
                startTime=datetime.combine(target_day, time(h, 0, tzinfo=timezone.utc)),
                publishTime=datetime(2026, 1, 9, 11, 0, tzinfo=timezone.utc),
                generation=10000.0,
            )
            for h in range(20)
        ]

        res = forecast_service.evaluate(
            actuals=actuals,
            forecasts=forecasts,
            from_date=target_day.isoformat(),
            to_date=target_day.isoformat(),
        )

        s = res.summary
        assert s.actualRecordsCount == 48
        assert s.matchedCount == 20
        assert s.unmatchedHalfHourlyActualsCount == 24
        assert s.missingHourlyForecastCount == 4

        # Invariant: 20 matched + 4 hourly missing forecast + 24 unmatched half-hourly = 48 actuals
        assert s.matchedCount + s.missingHourlyForecastCount + s.unmatchedHalfHourlyActualsCount == s.actualRecordsCount
