import { Alert, Box, Divider, Typography } from '@mui/material'
import Grid from '@mui/material/Grid'
import type { EvaluationResponse } from '../types/wind'
import { formatMW, formatNumber, formatPercent, formatSignedMW, isFiniteNumber } from '../utils/formatters'

interface MetricRowProps {
  label: string
  value: string | null
  description: string
}

function MetricRow({ label, value, description }: MetricRowProps) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </Typography>
      <Typography variant="h6" component="p" sx={{ fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
        {value ?? '—'}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {description}
      </Typography>
    </Box>
  )
}

export function biasInterpretation(bias: number | null | undefined): string {
  if (!isFiniteNumber(bias)) return 'Bias is not available.'
  const rounded = Number(bias.toFixed(1))
  if (rounded === 0) return 'Forecasts were unbiased on average (forecast − actual ≈ 0).'
  return bias > 0
    ? 'Positive bias: forecasts were higher than actual generation on average (over-forecasting).'
    : 'Negative bias: forecasts were lower than actual generation on average (under-forecasting).'
}

export default function AccuracyMetrics({ evaluation }: { evaluation: EvaluationResponse }) {
  const { metrics, matchedData, summary } = evaluation
  const hasSamples = metrics.sampleCount > 0
  const excludedFromMape = matchedData.filter((r) => r.percentageError === null).length

  return (
    <Box sx={{ display: 'grid', gap: 2.5 }}>
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
          <MetricRow label="MAE" value={hasSamples ? formatMW(metrics.maeMW) : null} description="Mean absolute error: average size of the forecast error, regardless of direction." />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
          <MetricRow label="RMSE" value={hasSamples ? formatMW(metrics.rmseMW) : null} description="Root mean squared error: like MAE but penalises large misses more heavily." />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
          <MetricRow label="Bias" value={hasSamples ? formatSignedMW(metrics.biasMW) : null} description="Mean of (forecast − actual). Positive = over-forecast, negative = under-forecast." />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
          <MetricRow label="nMAE" value={hasSamples ? formatPercent(metrics.nmaePercentage) : null} description="MAE divided by mean actual generation. Not available when mean actual is zero." />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
          <MetricRow label="MAPE" value={hasSamples ? formatPercent(metrics.mapePercentage) : null} description="Mean absolute percentage error, computed only for periods with actual > 0." />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 4 }}>
          <MetricRow label="Matched samples" value={formatNumber(metrics.sampleCount)} description="Hourly periods with both an eligible day-ahead forecast and an actual value." />
        </Grid>
      </Grid>

      {hasSamples && <Alert severity="info" variant="outlined">{biasInterpretation(metrics.biasMW)}</Alert>}

      {hasSamples && (
        <Alert severity={excludedFromMape > 0 ? 'warning' : 'info'} variant="outlined">
          MAPE can be unreliable when actual generation is zero or very low, because small absolute errors become very large percentages. Use MAE and nMAE as the primary measures.
          {excludedFromMape > 0 && ` ${formatNumber(excludedFromMape)} matched period(s) with zero actual generation are excluded from MAPE.`}
        </Alert>
      )}

      <Divider />
      <Typography variant="body2" color="text.secondary">
        Evaluated against the latest forecast published by the day-ahead cutoff ({summary.decisionCutoffRule}). Missing hourly forecasts: {formatNumber(summary.missingHourlyForecastCount)} · Missing hourly actuals: {formatNumber(summary.missingHourlyActualCount)} · Coverage: {formatPercent(summary.coveragePercentage, 2) ?? '—'}.
      </Typography>
    </Box>
  )
}
