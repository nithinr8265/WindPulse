import type { DateRangeParams } from '../types/wind'
import { parseIsoDate } from './formatters'

export const DEFAULT_RANGE: DateRangeParams = { fromDate: '2026-01-01', toDate: '2026-01-31' }

/** Ranges longer than this are allowed but flagged: the backend queries Elexon per request. */
export const LONG_RANGE_DAYS = 62

export interface RangeValidation {
  fromError: string | null
  toError: string | null
  rangeError: string | null
  valid: boolean
  days: number | null
}

/**
 * Mirrors the backend rules (YYYY-MM-DD calendar dates, from_date <= to_date).
 * Dates are compared as UTC calendar days; no local timezone conversion is applied.
 */
export function validateRange(fromDate: string, toDate: string): RangeValidation {
  const from = fromDate ? parseIsoDate(fromDate) : null
  const to = toDate ? parseIsoDate(toDate) : null
  const fromError = from ? null : fromDate ? 'Enter a valid date (YYYY-MM-DD).' : 'Start date is required.'
  const toError = to ? null : toDate ? 'Enter a valid date (YYYY-MM-DD).' : 'End date is required.'
  let rangeError: string | null = null
  let days: number | null = null
  if (from && to) {
    if (from.getTime() > to.getTime()) {
      rangeError = 'The start date must be on or before the end date.'
    } else {
      days = Math.round((to.getTime() - from.getTime()) / 86_400_000) + 1
    }
  }
  return { fromError, toError, rangeError, valid: !fromError && !toError && !rangeError, days }
}
