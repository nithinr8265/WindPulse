"""Forecast evaluation and data matching service module."""

import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple

from app.config import Settings, get_settings
from app.models.schemas import (
    AccuracyMetrics,
    EvaluationResponse,
    EvaluationSummary,
    MatchedRecord,
    WindActualRecord,
    WindForecastRecord,
)
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


def calculate_day_ahead_cutoff(target_time: datetime, cutoff_hour: int = 12) -> datetime:
    """Calculate the day-ahead purchasing decision deadline for a given target delivery time.

    In Great Britain electricity markets (e.g. EPEX SPOT Day-Ahead Auction), the day-ahead
    gate closure occurs at 12:00 UTC (noon) on the calendar day prior to physical delivery (D-1).

    Parameters:
        target_time: Target delivery half-hour start time (UTC).
        cutoff_hour: Hour of the day on D-1 for the decision cutoff (0-23, default 12).

    Returns:
        datetime representing D-1 at cutoff_hour:00:00 UTC.

    Example:
        For target_time = 2026-01-15 14:30:00 UTC and cutoff_hour = 12,
        the cutoff deadline is 2026-01-14 12:00:00 UTC.
    """
    # Normalize to UTC
    if target_time.tzinfo is None:
        target_time = target_time.replace(tzinfo=timezone.utc)
    else:
        target_time = target_time.astimezone(timezone.utc)

    target_date = target_time.date()
    day_before = target_date - timedelta(days=1)
    cutoff_dt = datetime.combine(day_before, time(hour=cutoff_hour, minute=0, second=0, tzinfo=timezone.utc))
    return cutoff_dt


class ForecastService:
    """Orchestrates forecast filtering, day-ahead selection, matching with actuals, and evaluation."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def select_day_ahead_forecasts(
        self,
        forecasts: List[WindForecastRecord],
        cutoff_hour: Optional[int] = None,
    ) -> Dict[datetime, WindForecastRecord]:
        """Select the single latest eligible forecast for each target startTime before the decision cutoff.

        Fair evaluation rule:
        1. For each target `startTime`, calculate the day-ahead cutoff deadline (D-1 at cutoff_hour UTC).
        2. Filter out any forecast where `publishTime > cutoff_deadline` to strictly avoid data leakage.
        3. Among all eligible forecasts for that target `startTime`, choose the latest published forecast:
           max(publishTime).
        4. If duplicate records exist for the same target time and publish time, deduplicate deterministically.

        Parameters:
            forecasts: List of raw WindForecastRecord instances.
            cutoff_hour: Day-ahead cutoff hour on D-1 (defaults to configured setting, e.g. 12 UTC).

        Returns:
            Dictionary mapping target `startTime` (datetime) -> selected `WindForecastRecord`.
        """
        hour = cutoff_hour if cutoff_hour is not None else self.settings.DAY_AHEAD_DECISION_CUTOFF_HOUR

        # Group eligible forecasts by target startTime
        eligible_by_target: Dict[datetime, List[WindForecastRecord]] = defaultdict(list)
        leakage_excluded_count = 0

        for f in forecasts:
            # Ensure UTC timezone
            start_utc = f.startTime if f.startTime.tzinfo else f.startTime.replace(tzinfo=timezone.utc)
            pub_utc = f.publishTime if f.publishTime.tzinfo else f.publishTime.replace(tzinfo=timezone.utc)

            cutoff_deadline = calculate_day_ahead_cutoff(start_utc, cutoff_hour=hour)

            # Strict data leakage check: forecast must have been published BEFORE or AT the decision cutoff
            if pub_utc <= cutoff_deadline:
                eligible_by_target[start_utc].append(f)
            else:
                leakage_excluded_count += 1

        logger.debug(
            "Forecast filtering: %d eligible targets, %d post-cutoff forecasts excluded (leakage prevention)",
            len(eligible_by_target),
            leakage_excluded_count,
        )

        # For each target time, select the forecast with the latest publishTime
        selected_forecasts: Dict[datetime, WindForecastRecord] = {}
        for target_time, candidates in eligible_by_target.items():
            # Pick latest publication time
            best_forecast = max(candidates, key=lambda c: c.publishTime)
            selected_forecasts[target_time] = best_forecast

        return selected_forecasts

    def match_forecasts_and_actuals(
        self,
        actuals: List[WindActualRecord],
        forecasts: List[WindForecastRecord],
        cutoff_hour: Optional[int] = None,
        expected_hourly_targets: Optional[List[datetime]] = None,
    ) -> Tuple[List[MatchedRecord], int, int, int]:
        """Match actual generation records with eligible day-ahead forecasts by target startTime.

        Parameters:
            actuals: List of WindActualRecord instances (contains :00 and :30 settlement periods).
            forecasts: List of WindForecastRecord instances (hourly :00 start times).
            cutoff_hour: Day-ahead cutoff hour on D-1.
            expected_hourly_targets: Optional list of all expected hourly delivery datetimes (UTC)
                                     in the evaluation window.

        Returns:
            Tuple of:
            - matched_records: List of MatchedRecord objects for matched hourly periods
            - missing_hourly_forecast_count: Count of hourly target periods lacking an eligible forecast
            - missing_hourly_actual_count: Count of hourly target periods lacking actual generation at :00
            - unmatched_half_hourly_actuals_count: Count of half-hourly actuals (:30) lacking WINDFOR forecasts
        """
        hour = cutoff_hour if cutoff_hour is not None else self.settings.DAY_AHEAD_DECISION_CUTOFF_HOUR

        # If expected hourly targets are provided, establish window boundaries [min_target, max_target + 1h)
        # to ensure out-of-window actuals are not accidentally partitioned or counted.
        if expected_hourly_targets:
            window_start = min(expected_hourly_targets)
            window_end = max(expected_hourly_targets) + timedelta(hours=1)
        else:
            window_start = None
            window_end = None

        # Deduplicate and separate actuals into hourly (:00) and half-hourly (:30)
        hourly_actuals: Dict[datetime, WindActualRecord] = {}
        half_hourly_actuals: Dict[datetime, WindActualRecord] = {}

        for act in actuals:
            start_utc = act.startTime if act.startTime.tzinfo else act.startTime.replace(tzinfo=timezone.utc)
            if window_start is not None and window_end is not None:
                if not (window_start <= start_utc < window_end):
                    continue

            if start_utc.minute == 0:
                hourly_actuals[start_utc] = act
            else:
                half_hourly_actuals[start_utc] = act

        # Elexon WINDFOR only publishes hourly forecasts (:00), so all :30 actuals are unmatched
        unmatched_half_hourly_actuals_count = len(half_hourly_actuals)

        # Select latest eligible day-ahead forecasts (one per target hour)
        selected_forecasts = self.select_day_ahead_forecasts(forecasts, cutoff_hour=hour)

        matched_records: List[MatchedRecord] = []

        # Determine target hourly timeline
        if expected_hourly_targets is not None:
            target_hours = sorted(set(expected_hourly_targets))
        else:
            target_hours = sorted(set(hourly_actuals.keys()).union(set(selected_forecasts.keys())))

        missing_hourly_forecast_count = 0
        missing_hourly_actual_count = 0

        for target_time in target_hours:
            act = hourly_actuals.get(target_time)
            fc = selected_forecasts.get(target_time)

            if act is not None and fc is not None:
                # Both actual (:00) and eligible forecast exist: match
                cutoff_dt = calculate_day_ahead_cutoff(target_time, cutoff_hour=hour)
                error_mw = fc.generation - act.generation
                abs_error_mw = abs(error_mw)
                pct_error = (abs_error_mw / act.generation * 100.0) if act.generation > 0 else None

                target_date_str = target_time.strftime("%Y-%m-%d")

                matched = MatchedRecord(
                    startTime=target_time,
                    targetDate=target_date_str,
                    settlementPeriod=act.settlementPeriod,
                    actualGenerationMW=round(act.generation, 2),
                    forecastGenerationMW=round(fc.generation, 2),
                    forecastPublishTime=fc.publishTime,
                    decisionCutoffTime=cutoff_dt,
                    errorMW=round(error_mw, 2),
                    absoluteErrorMW=round(abs_error_mw, 2),
                    percentageError=round(pct_error, 2) if pct_error is not None else None,
                )
                matched_records.append(matched)
            elif act is not None and fc is None:
                # Expected hour had actual generation recorded, but no eligible day-ahead forecast
                missing_hourly_forecast_count += 1
            elif act is None and fc is not None:
                # Forecast was issued, but no actual generation at :00 was recorded
                missing_hourly_actual_count += 1
            else:
                # Neither actual nor forecast exists for this expected hour
                missing_hourly_forecast_count += 1
                missing_hourly_actual_count += 1

        # Sort matched records chronologically
        matched_records.sort(key=lambda r: r.startTime)
        return (
            matched_records,
            missing_hourly_forecast_count,
            missing_hourly_actual_count,
            unmatched_half_hourly_actuals_count,
        )

    def evaluate(
        self,
        actuals: List[WindActualRecord],
        forecasts: List[WindForecastRecord],
        from_date: str = "2026-01-01",
        to_date: str = "2026-01-31",
        cutoff_hour: Optional[int] = None,
    ) -> EvaluationResponse:
        """Run full evaluation workflow over actual and forecast datasets for the requested date window.

        Parameters:
            actuals: Retrieved WindActualRecord items (half-hourly FUELHH).
            forecasts: Retrieved WindForecastRecord items (hourly WINDFOR revisions).
            from_date: Evaluation start date (YYYY-MM-DD).
            to_date: Evaluation end date (YYYY-MM-DD).
            cutoff_hour: Decision cutoff hour on D-1 (e.g. 12 UTC).

        Returns:
            EvaluationResponse with summary statistics, quantitative accuracy metrics, and matched timeseries.
        """
        hour = cutoff_hour if cutoff_hour is not None else self.settings.DAY_AHEAD_DECISION_CUTOFF_HOUR

        start_d = date.fromisoformat(from_date)
        end_d = date.fromisoformat(to_date)
        total_days = (end_d - start_d).days + 1

        # In Great Britain electricity markets:
        # - WINDFOR forecasts are published at hourly resolution: 24 expected forecast targets per day.
        # - FUELHH actuals are metered at half-hourly resolution: 48 settlement periods per day.
        total_expected_hourly_periods = total_days * 24
        total_actual_half_hourly_periods = total_days * 48

        # Define strict UTC evaluation window boundaries [target_start, target_end)
        target_start = datetime.combine(start_d, time.min, tzinfo=timezone.utc)
        target_end = datetime.combine(end_d + timedelta(days=1), time.min, tzinfo=timezone.utc)

        # Build full timeline of all expected hourly delivery points in the evaluation window
        expected_hourly_targets: List[datetime] = [
            datetime.combine(
                start_d + timedelta(days=d),
                time(hour=h, minute=0, second=0, tzinfo=timezone.utc),
            )
            for d in range(total_days)
            for h in range(24)
        ]

        # Filter actuals strictly to the in-scope evaluation window [target_start, target_end)
        # Out-of-window actuals are excluded prior to matching to prevent silent count leakage
        in_scope_actuals: List[WindActualRecord] = [
            act
            for act in actuals
            if target_start <= (act.startTime if act.startTime.tzinfo else act.startTime.replace(tzinfo=timezone.utc)) < target_end
        ]

        out_of_window_count = len(actuals) - len(in_scope_actuals)
        if out_of_window_count > 0:
            logger.debug(
                "Excluded %d out-of-window actual records outside [%s, %s)",
                out_of_window_count,
                target_start.isoformat(),
                target_end.isoformat(),
            )

        # Match actuals and eligible forecasts
        (
            matched_records,
            missing_forecast_count,
            missing_actual_count,
            unmatched_half_hourly_actuals_count,
        ) = self.match_forecasts_and_actuals(
            actuals=in_scope_actuals,
            forecasts=forecasts,
            cutoff_hour=hour,
            expected_hourly_targets=expected_hourly_targets,
        )

        # Count eligible day-ahead forecasts (one per target hour)
        selected_forecasts = self.select_day_ahead_forecasts(forecasts, cutoff_hour=hour)
        eligible_forecasts_count = len(selected_forecasts)

        # Calculate quantitative accuracy metrics over matched records
        metrics = MetricsService.calculate_metrics(matched_records)

        # Coverage is measured against expected hourly forecast target periods
        coverage_pct = (
            round((len(matched_records) / total_expected_hourly_periods) * 100.0, 2)
            if total_expected_hourly_periods > 0
            else 0.0
        )

        start_dt = datetime.combine(start_d, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(end_d, time(23, 30, 0), tzinfo=timezone.utc)

        summary = EvaluationSummary(
            targetPeriodStart=start_dt,
            targetPeriodEnd=end_dt,
            decisionCutoffRule=f"Day-Ahead (D-1 at {hour:02d}:00 UTC)",
            totalExpectedHourlyPeriods=total_expected_hourly_periods,
            totalActualHalfHourlyPeriods=total_actual_half_hourly_periods,
            rawForecastRevisionsCount=len(forecasts),
            eligibleForecastsCount=eligible_forecasts_count,
            matchedCount=len(matched_records),
            missingHourlyForecastCount=missing_forecast_count,
            missingHourlyActualCount=missing_actual_count,
            unmatchedHalfHourlyActualsCount=unmatched_half_hourly_actuals_count,
            coveragePercentage=coverage_pct,
            # Backward-compatibility aliases
            totalExpectedPeriods=total_expected_hourly_periods,
            actualRecordsCount=len(in_scope_actuals),
            forecastRecordsCount=len(forecasts),
            missingForecastCount=missing_forecast_count,
            missingActualCount=missing_actual_count,
        )

        return EvaluationResponse(
            status="success",
            summary=summary,
            metrics=metrics,
            matchedData=matched_records,
        )
