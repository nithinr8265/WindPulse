import type { EvaluationResponse, MatchedRecord } from '../src/types/wind'

export function makeMatched(hourUtc: number, actual: number, forecast: number, day = '2026-01-01'): MatchedRecord {
  const hh = String(hourUtc).padStart(2, '0')
  const error = forecast - actual
  return {
    startTime: `${day}T${hh}:00:00Z`,
    targetDate: day,
    settlementPeriod: hourUtc * 2 + 1,
    actualGenerationMW: actual,
    forecastGenerationMW: forecast,
    forecastPublishTime: '2025-12-31T11:00:00Z',
    decisionCutoffTime: '2025-12-31T12:00:00Z',
    errorMW: error,
    absoluteErrorMW: Math.abs(error),
    percentageError: actual > 0 ? (Math.abs(error) / actual) * 100 : null,
  }
}

/** Test fixture only - never used by application code. */
export function makeEvaluation(overrides: Partial<EvaluationResponse> = {}): EvaluationResponse {
  const matchedData = [makeMatched(0, 1000, 1100), makeMatched(1, 2000, 1900), makeMatched(2, 3000, 3300)]
  return {
    status: 'success',
    summary: {
      targetPeriodStart: '2026-01-01T00:00:00Z',
      targetPeriodEnd: '2026-01-31T23:30:00Z',
      decisionCutoffRule: 'Day-Ahead (D-1 at 12:00 UTC)',
      totalExpectedHourlyPeriods: 744,
      totalActualHalfHourlyPeriods: 1488,
      rawForecastRevisionsCount: 5000,
      eligibleForecastsCount: 700,
      matchedCount: 3,
      missingHourlyForecastCount: 44,
      missingHourlyActualCount: 2,
      unmatchedHalfHourlyActualsCount: 744,
      coveragePercentage: 94.09,
      totalExpectedPeriods: 744,
      actualRecordsCount: 1488,
      forecastRecordsCount: 5000,
      missingForecastCount: 44,
      missingActualCount: 2,
    },
    metrics: {
      sampleCount: 3,
      maeMW: 166.67,
      rmseMW: 182.57,
      biasMW: 100,
      nmaePercentage: 8.33,
      mapePercentage: 8.89,
      meanActualMW: 2000,
      meanForecastMW: 2100,
      unit: 'MW',
      definitions: {},
    },
    matchedData,
    ...overrides,
  }
}
