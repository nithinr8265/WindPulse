/**
 * Types mirroring the backend Pydantic models in app/models/schemas.py.
 * Datetimes are serialised by FastAPI as ISO-8601 strings (UTC).
 */

export interface HealthResponse {
  status: string
  app_name: string
  timestamp: string
  environment: string
}

export interface WindActualRecord {
  startTime: string
  generation: number
  fuelType: string
  settlementDate: string | null
  settlementPeriod: number | null
}

export interface WindForecastRecord {
  startTime: string
  publishTime: string
  generation: number
  dataset: string | null
}

export interface ActualsResponse {
  status: string
  count: number
  fromDate: string
  toDate: string
  data: WindActualRecord[]
}

export interface ForecastsResponse {
  status: string
  count: number
  fromDate: string
  toDate: string
  data: WindForecastRecord[]
}

export interface MatchedRecord {
  startTime: string
  targetDate: string
  settlementPeriod: number | null
  actualGenerationMW: number
  forecastGenerationMW: number
  forecastPublishTime: string
  decisionCutoffTime: string
  /** Forecast - Actual. Positive = over-forecast. */
  errorMW: number
  absoluteErrorMW: number
  percentageError: number | null
}

export interface AccuracyMetrics {
  sampleCount: number
  maeMW: number
  rmseMW: number
  /** Mean (Forecast - Actual). Positive = over-forecast. */
  biasMW: number
  nmaePercentage: number | null
  mapePercentage: number | null
  meanActualMW: number
  meanForecastMW: number
  unit: string
  definitions: Record<string, string>
}

export interface EvaluationSummary {
  targetPeriodStart: string
  targetPeriodEnd: string
  decisionCutoffRule: string
  totalExpectedHourlyPeriods: number
  totalActualHalfHourlyPeriods: number
  rawForecastRevisionsCount: number
  eligibleForecastsCount: number
  matchedCount: number
  missingHourlyForecastCount: number
  missingHourlyActualCount: number
  unmatchedHalfHourlyActualsCount: number
  coveragePercentage: number
  // Backward-compatibility aliases returned by the backend
  totalExpectedPeriods: number
  actualRecordsCount: number
  forecastRecordsCount: number
  missingForecastCount: number
  missingActualCount: number
}

export interface EvaluationResponse {
  status: string
  summary: EvaluationSummary
  metrics: AccuracyMetrics
  matchedData: MatchedRecord[]
}

/** Query parameters supported by the backend (snake_case on the wire). */
export interface DateRangeParams {
  /** YYYY-MM-DD */
  fromDate: string
  /** YYYY-MM-DD */
  toDate: string
}

export interface RecordListParams extends DateRangeParams {
  limit?: number
}

export interface EvaluationParams extends DateRangeParams {
  /** Day-ahead cutoff hour on D-1 (0-23 UTC). Backend default: 12. */
  cutoffHour?: number
  /** Backend default: true. */
  includeTimeseries?: boolean
}
