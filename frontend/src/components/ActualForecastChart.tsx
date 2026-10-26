import { useMemo } from 'react'
import { Box, Typography } from '@mui/material'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { TooltipContentProps } from 'recharts'
import type { MatchedRecord } from '../types/wind'
import { buildChartSeries, countGaps, HOUR_MS, type ChartPoint } from '../utils/chartData'
import { formatMW, formatNumber, formatSignedMW, formatUtcDateTime } from '../utils/formatters'
import { palette } from '../theme'

interface ActualForecastChartProps {
  matchedData: readonly MatchedRecord[]
}

const tickFormatterFor = (spanMs: number) => (value: number) => {
  const date = new Date(value)
  const opts: Intl.DateTimeFormatOptions =
    spanMs <= 3 * 24 * HOUR_MS
      ? { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'UTC' }
      : { day: '2-digit', month: 'short', timeZone: 'UTC' }
  return new Intl.DateTimeFormat('en-GB', opts).format(date)
}

function ChartTooltip({ active, payload }: TooltipContentProps) {
  const point = payload?.[0]?.payload as ChartPoint | undefined
  if (!active || !point || point.gap || !point.record) return null
  const r = point.record
  return (
    <Box sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: 1, p: 1.5, boxShadow: 2, minWidth: 220 }}>
      <Typography variant="subtitle2">{formatUtcDateTime(r.startTime)}</Typography>
      <Typography variant="body2" sx={{ color: palette.actual }}>Actual: {formatMW(r.actualGenerationMW)}</Typography>
      <Typography variant="body2" sx={{ color: palette.forecast }}>Day-ahead forecast: {formatMW(r.forecastGenerationMW)}</Typography>
      <Typography variant="body2" color="text.secondary">Error (forecast − actual): {formatSignedMW(r.errorMW)}</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
        Forecast published {formatUtcDateTime(r.forecastPublishTime)}
      </Typography>
    </Box>
  )
}

export default function ActualForecastChart({ matchedData }: ActualForecastChartProps) {
  const points = useMemo(() => buildChartSeries(matchedData), [matchedData])
  const gaps = countGaps(points)
  const real = points.filter((p) => !p.gap)

  if (real.length === 0) {
    return (
      <Typography color="text.secondary">
        No matched hourly periods to plot for this date range. Actual and forecast values are only shown where both exist.
      </Typography>
    )
  }

  const span = real[real.length - 1].ts - real[0].ts
  const description = `Line chart of actual and day-ahead forecast wind generation in MW for ${formatNumber(real.length)} matched hourly periods, from ${formatUtcDateTime(new Date(real[0].ts).toISOString())} to ${formatUtcDateTime(new Date(real[real.length - 1].ts).toISOString())}.`

  return (
    <Box>
      <Box role="img" aria-label={description} sx={{ width: '100%', height: { xs: 280, md: 380 } }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={points} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={palette.border} />
            <XAxis
              dataKey="ts"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tickFormatter={tickFormatterFor(span)}
              tick={{ fontSize: 12 }}
              minTickGap={32}
              label={{ value: 'Time (UTC)', position: 'insideBottom', offset: -2, fontSize: 12 }}
              height={44}
            />
            <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => formatNumber(v) ?? ''} width={64} label={{ value: 'Generation (MW)', angle: -90, position: 'insideLeft', fontSize: 12, offset: 8 }} />
            <Tooltip content={ChartTooltip} />
            <Legend verticalAlign="top" height={32} />
            <Line type="monotone" dataKey="actual" name="Actual generation" stroke={palette.actual} strokeWidth={2} dot={false} activeDot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="forecast" name="Day-ahead forecast" stroke={palette.forecast} strokeWidth={2} dot={false} activeDot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
        Plots hourly periods that have both an actual value and an eligible day-ahead forecast
        {gaps > 0 ? `. Lines break at ${formatNumber(gaps)} gap(s) where hourly periods are missing; missing values are not interpolated or treated as zero.` : '.'}
        {' '}Half-hourly actuals at :30 have no matching WINDFOR forecast and are not plotted.
      </Typography>
    </Box>
  )
}
