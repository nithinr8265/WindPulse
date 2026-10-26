"""Metrics service for evaluating wind generation forecast accuracy."""

import math
from typing import List, Optional, Tuple
from app.models.schemas import AccuracyMetrics, MatchedRecord


class MetricsCalculationError(Exception):
    """Raised when an error occurs during accuracy metrics calculation."""
    pass


class MetricsService:
    """Calculates quantitative forecast accuracy metrics with explicit units and definitions."""

    @staticmethod
    def calculate_metrics(matched_records: List[MatchedRecord]) -> AccuracyMetrics:
        """Calculate quantitative accuracy metrics for a collection of matched forecast-actual pairs.

        Metrics calculated:
        - MAE (Mean Absolute Error) in MW: (1/N) * sum(|Forecast - Actual|)
        - RMSE (Root Mean Squared Error) in MW: sqrt((1/N) * sum((Forecast - Actual)^2))
        - Bias (Mean Forecast Error) in MW: (1/N) * sum(Forecast - Actual)
        - nMAE (Normalized MAE) in %: (MAE / Mean(Actual)) * 100
        - MAPE (Mean Absolute Percentage Error) in %: mean(|Forecast - Actual| / Actual) * 100 for Actual > 0

        Parameters:
            matched_records: List of MatchedRecord objects containing actual and forecast values.

        Returns:
            AccuracyMetrics instance populated with values and human-readable definitions.
        """
        n = len(matched_records)
        if n == 0:
            return AccuracyMetrics(
                sampleCount=0,
                maeMW=0.0,
                rmseMW=0.0,
                biasMW=0.0,
                nmaePercentage=None,
                mapePercentage=None,
                meanActualMW=0.0,
                meanForecastMW=0.0,
                unit="MW",
            )

        sum_abs_err = 0.0
        sum_sq_err = 0.0
        sum_err = 0.0
        sum_actual = 0.0
        sum_forecast = 0.0

        percentage_errors: List[float] = []

        for record in matched_records:
            actual = record.actualGenerationMW
            forecast = record.forecastGenerationMW

            # Error definition: Forecast - Actual
            error = forecast - actual
            abs_error = abs(error)

            sum_err += error
            sum_abs_err += abs_error
            sum_sq_err += error * error
            sum_actual += actual
            sum_forecast += forecast

            # Avoid division by zero: only compute percentage error when actual > 0
            if actual > 0:
                percentage_errors.append((abs_error / actual) * 100.0)

        mae = sum_abs_err / n
        rmse = math.sqrt(sum_sq_err / n)
        bias = sum_err / n
        mean_actual = sum_actual / n
        mean_forecast = sum_forecast / n

        # Normalized MAE: relative to mean actual generation
        nmae = (mae / mean_actual * 100.0) if mean_actual > 0 else None

        # Mean Absolute Percentage Error
        mape = (sum(percentage_errors) / len(percentage_errors)) if percentage_errors else None

        return AccuracyMetrics(
            sampleCount=n,
            maeMW=round(mae, 2),
            rmseMW=round(rmse, 2),
            biasMW=round(bias, 2),
            nmaePercentage=round(nmae, 2) if nmae is not None else None,
            mapePercentage=round(mape, 2) if mape is not None else None,
            meanActualMW=round(mean_actual, 2),
            meanForecastMW=round(mean_forecast, 2),
            unit="MW",
        )
