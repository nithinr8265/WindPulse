import { Alert, Box, LinearProgress, Stack, Typography } from '@mui/material'
import Grid from '@mui/material/Grid'
import type { EvaluationSummary } from '../types/wind'
import { formatNumber, formatPercent, formatUtcDateTime } from '../utils/formatters'

interface StatProps {
  label: string
  value: number
  description: string
  emphasis?: 'warning'
}

function Stat({ label, value, description, emphasis }: StatProps) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </Typography>
      <Typography variant="h6" component="p" sx={{ fontWeight: 700, fontVariantNumeric: 'tabular-nums', color: emphasis === 'warning' && value > 0 ? 'warning.dark' : 'text.primary' }}>
        {formatNumber(value) ?? '—'}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {description}
      </Typography>
    </Box>
  )
}

export interface CoverageWarning {
  severity: 'warning' | 'info'
  message: string
}

/** Derives data-quality messages strictly from the backend summary counts. */
export function coverageWarnings(s: EvaluationSummary): CoverageWarning[] {
  const out: CoverageWarning[] = []
  if (s.coveragePercentage < 100) {
    out.push({
      severity: 'warning',
      message: `Coverage is incomplete: ${formatNumber(s.matchedCount)} of ${formatNumber(s.totalExpectedHourlyPeriods)} expected hourly periods (${formatPercent(s.coveragePercentage, 2)}) were matched. Accuracy metrics describe matched periods only.`,
    })
  }
  if (s.missingHourlyForecastCount > 0) {
    out.push({
      severity: 'warning',
      message: `${formatNumber(s.missingHourlyForecastCount)} expected hourly period(s) have no eligible day-ahead forecast (none published by the cutoff), so no purchase-time forecast exists for them.`,
    })
  }
  if (s.missingHourlyActualCount > 0) {
    out.push({
      severity: 'warning',
      message: `${formatNumber(s.missingHourlyActualCount)} expected hourly period(s) have a forecast but no actual generation record at :00, so their forecast error cannot be measured.`,
    })
  }
  if (s.unmatchedHalfHourlyActualsCount > 0) {
    out.push({
      severity: 'info',
      message: `${formatNumber(s.unmatchedHalfHourlyActualsCount)} half-hourly actual record(s) (at :30) have no matching forecast, because WINDFOR forecasts are hourly. They are not evaluated, even when hourly coverage is 100%.`,
    })
  }
  return out
}

export default function DataCoverage({ summary }: { summary: EvaluationSummary }) {
  const warnings = coverageWarnings(summary)
  const coverage = Math.max(0, Math.min(100, summary.coveragePercentage))

  return (
    <Box sx={{ display: 'grid', gap: 3 }}>
      <Box>
        <Stack direction="row" sx={{ justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>Hourly forecast coverage</Typography>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>{formatPercent(summary.coveragePercentage, 2) ?? '—'}</Typography>
        </Stack>
        <LinearProgress variant="determinate" value={coverage} color={coverage >= 100 ? 'success' : 'warning'} aria-label="Hourly forecast coverage" sx={{ height: 8, borderRadius: 4 }} />
        <Typography variant="caption" color="text.secondary">
          Matched hourly periods ÷ expected hourly periods. Window: {formatUtcDateTime(summary.targetPeriodStart)} to {formatUtcDateTime(summary.targetPeriodEnd)}. Cutoff rule: {summary.decisionCutoffRule}.
        </Typography>
      </Box>

      <Box>
        <Typography variant="h3" component="h3" sx={{ mb: 1.5 }}>Hourly forecast evaluation</Typography>
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}><Stat label="Expected hourly periods" value={summary.totalExpectedHourlyPeriods} description="24 per day in the selected range." /></Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}><Stat label="Raw forecast revisions" value={summary.rawForecastRevisionsCount} description="Every WINDFOR publication retrieved. Revisions are not evaluation samples." /></Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}><Stat label="Eligible forecasts" value={summary.eligibleForecastsCount} description="Target hours with a forecast published by the cutoff (latest one selected)." /></Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}><Stat label="Matched hourly periods" value={summary.matchedCount} description="Hours with both an eligible forecast and an actual value; the evaluation sample." /></Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}><Stat label="Missing hourly forecasts" value={summary.missingHourlyForecastCount} emphasis="warning" description="Expected hours with no eligible day-ahead forecast." /></Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}><Stat label="Missing hourly actuals" value={summary.missingHourlyActualCount} emphasis="warning" description="Expected hours with no actual record at :00." /></Grid>
        </Grid>
      </Box>

      <Box>
        <Typography variant="h3" component="h3" sx={{ mb: 1.5 }}>Half-hourly actuals</Typography>
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}><Stat label="Expected half-hourly periods" value={summary.totalActualHalfHourlyPeriods} description="48 per day in the selected range." /></Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}><Stat label="Actual records retrieved" value={summary.actualRecordsCount} description="FUELHH wind records returned for the range." /></Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 4 }}><Stat label="Unmatched half-hourly actuals" value={summary.unmatchedHalfHourlyActualsCount} description="Actuals at :30 that have no hourly forecast to compare with." /></Grid>
        </Grid>
      </Box>

      {warnings.length === 0 ? (
        <Alert severity="success" variant="outlined">All expected hourly periods were matched and no data gaps were reported.</Alert>
      ) : (
        <Stack spacing={1}>
          {warnings.map((w) => (
            <Alert key={w.message} severity={w.severity} variant="outlined">{w.message}</Alert>
          ))}
        </Stack>
      )}
    </Box>
  )
}
