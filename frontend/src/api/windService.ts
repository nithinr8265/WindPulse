import { apiClient, toApiError } from './client'
import type {
  ActualsResponse,
  EvaluationParams,
  EvaluationResponse,
  ForecastsResponse,
  HealthResponse,
  RecordListParams,
} from '../types/wind'

async function get<T>(url: string, params?: Record<string, unknown>, signal?: AbortSignal): Promise<T> {
  try {
    const response = await apiClient.get<T>(url, { params, signal })
    return response.data
  } catch (error) {
    throw toApiError(error)
  }
}

/** GET /health */
export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return get<HealthResponse>('/health', undefined, signal)
}

/** GET /api/v1/wind/actuals - half-hourly FUELHH wind actuals (fuelType == WIND). */
export function getActuals(params: RecordListParams, signal?: AbortSignal): Promise<ActualsResponse> {
  return get<ActualsResponse>(
    '/api/v1/wind/actuals',
    { from_date: params.fromDate, to_date: params.toDate, limit: params.limit },
    signal,
  )
}

/** GET /api/v1/wind/forecasts - raw WINDFOR forecast revisions. */
export function getForecasts(params: RecordListParams, signal?: AbortSignal): Promise<ForecastsResponse> {
  return get<ForecastsResponse>(
    '/api/v1/wind/forecasts',
    { from_date: params.fromDate, to_date: params.toDate, limit: params.limit },
    signal,
  )
}

/** GET /api/v1/wind/evaluation - day-ahead evaluation (summary, metrics, matchedData). */
export function getEvaluation(params: EvaluationParams, signal?: AbortSignal): Promise<EvaluationResponse> {
  return get<EvaluationResponse>(
    '/api/v1/wind/evaluation',
    {
      from_date: params.fromDate,
      to_date: params.toDate,
      cutoff_hour: params.cutoffHour,
      include_timeseries: params.includeTimeseries,
    },
    signal,
  )
}
