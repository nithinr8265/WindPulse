import { useEffect, useState } from 'react'
import { getEvaluation } from '../api/windService'
import { ApiError, toApiError } from '../api/client'
import type { DateRangeParams, EvaluationResponse } from '../types/wind'

interface Result {
  key: string
  data?: EvaluationResponse
  error?: ApiError
  fetchedAt?: Date
}

export interface EvaluationState {
  data: EvaluationResponse | null
  error: ApiError | null
  loading: boolean
  fetchedAt: Date | null
}

/**
 * Loads the day-ahead evaluation (summary + metrics + matchedData) for a date range.
 * One request feeds the KPI cards, accuracy section, chart and coverage panel, so the
 * backend only does the Elexon fetch/matching work once per range. A newer request
 * aborts the previous one, and `refreshToken` forces a reload of the same range.
 */
export function useEvaluation({ fromDate, toDate }: DateRangeParams, refreshToken: number): EvaluationState {
  const key = `${fromDate}|${toDate}|${refreshToken}`
  const [result, setResult] = useState<Result | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    getEvaluation({ fromDate, toDate, includeTimeseries: true }, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, data, fetchedAt: new Date() })
      })
      .catch((e: unknown) => {
        const error = toApiError(e)
        if (!controller.signal.aborted && error.kind !== 'cancelled') setResult({ key, error })
      })
    return () => controller.abort()
  }, [key, fromDate, toDate])

  const settled = result?.key === key ? result : null
  return {
    data: settled?.data ?? null,
    error: settled?.error ?? null,
    loading: settled === null,
    fetchedAt: settled?.fetchedAt ?? null,
  }
}
