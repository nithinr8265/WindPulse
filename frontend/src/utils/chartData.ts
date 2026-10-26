import type { MatchedRecord } from '../types/wind'

export const HOUR_MS = 3_600_000

export interface ChartPoint {
  /** Epoch milliseconds (UTC) of the hourly period start. */
  ts: number
  actual: number | null
  forecast: number | null
  /** True for a value-less marker inserted only so the line breaks across a missing period. */
  gap?: true
  record?: MatchedRecord
}

/**
 * Converts the backend's matchedData into chart points.
 *
 * Only real matched records carry values. Where one or more expected hourly periods are
 * missing between two records, a single marker with null values is inserted so the lines
 * visibly break instead of being drawn straight across the gap. Nothing is interpolated
 * and missing periods are never treated as zero.
 */
export function buildChartSeries(matched: readonly MatchedRecord[]): ChartPoint[] {
  const records = matched
    .map((record) => ({ record, ts: Date.parse(record.startTime) }))
    .filter((r) => Number.isFinite(r.ts))
    .sort((a, b) => a.ts - b.ts)

  const points: ChartPoint[] = []
  let previous: number | null = null
  for (const { record, ts } of records) {
    if (previous !== null && ts - previous > HOUR_MS) {
      points.push({ ts: previous + HOUR_MS, actual: null, forecast: null, gap: true })
    }
    points.push({ ts, actual: record.actualGenerationMW, forecast: record.forecastGenerationMW, record })
    previous = ts
  }
  return points
}

/** Number of distinct runs of consecutive matched hours that are separated by a gap. */
export function countGaps(points: readonly ChartPoint[]): number {
  return points.filter((p) => p.gap).length
}
