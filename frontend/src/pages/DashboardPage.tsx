import { lazy, Suspense, useState } from 'react'
import { Alert, Box } from '@mui/material'
import Grid from '@mui/material/Grid'
import AppLayout from '../components/AppLayout'
import KpiCard from '../components/KpiCard'
import SectionCard from '../components/SectionCard'
import AccuracyMetrics from '../components/AccuracyMetrics'
import ErrorState from '../components/ErrorState'
import LoadingState from '../components/LoadingState'
import DataCoverage from '../components/DataCoverage'
import DateRangeFilter from '../components/DateRangeFilter'
import { useEvaluation } from '../hooks/useEvaluation'
import { useHealth } from '../hooks/useHealth'
import { palette } from '../theme'
import { formatMW, formatPercent, formatRange, formatSignedMW, formatUtcTime } from '../utils/formatters'
import type { DateRangeParams } from '../types/wind'
import { DEFAULT_RANGE } from '../utils/dateRange'

// Recharts is the largest dependency; load it only when the chart section renders.
const ActualForecastChart = lazy(() => import('../components/ActualForecastChart'))

export default function DashboardPage() {
  const [range, setRange] = useState<DateRangeParams>(DEFAULT_RANGE)
  const [refreshToken, setRefreshToken] = useState(0)
  const refresh = () => setRefreshToken((t) => t + 1)

  const health = useHealth(refreshToken)
  const evaluation = useEvaluation(range, refreshToken)
  const { data, error, loading, fetchedAt } = evaluation
  const hasSamples = (data?.metrics.sampleCount ?? 0) > 0
  const metrics = data?.metrics
  const biasValue = hasSamples ? metrics!.biasMW : null

  let biasHelper = 'Forecast − actual'
  if (biasValue !== null) {
    biasHelper = Number(biasValue.toFixed(1)) === 0 ? 'No average bias' : biasValue > 0 ? 'Over-forecasting on average' : 'Under-forecasting on average'
  }

  const kpis = [
    { label: 'Mean actual', value: hasSamples ? formatMW(metrics!.meanActualMW, 0) : null, accent: palette.actual, helper: 'Matched hourly periods', description: 'Average actual wind generation across matched hourly periods.' },
    { label: 'Mean forecast', value: hasSamples ? formatMW(metrics!.meanForecastMW, 0) : null, accent: palette.forecast, helper: 'Day-ahead forecast', description: 'Average of the selected day-ahead forecasts across matched hourly periods.' },
    { label: 'MAE', value: hasSamples ? formatMW(metrics!.maeMW) : null, accent: palette.muted, helper: 'Mean absolute error', description: 'Average magnitude of the forecast error in MW.' },
    { label: 'RMSE', value: hasSamples ? formatMW(metrics!.rmseMW) : null, accent: palette.muted, helper: 'Root mean squared error', description: 'Error measure that penalises large misses more heavily than MAE.' },
    { label: 'Bias', value: hasSamples ? formatSignedMW(biasValue) : null, accent: palette.warning, helper: biasHelper, description: 'Mean of (forecast − actual). Positive means over-forecasting.' },
    { label: 'nMAE', value: hasSamples ? formatPercent(metrics!.nmaePercentage) : null, accent: palette.muted, helper: 'MAE ÷ mean actual', description: 'MAE as a percentage of mean actual generation.' },
    { label: 'Coverage', value: data ? formatPercent(data.summary.coveragePercentage, 1) : null, accent: palette.actual, helper: data ? `${data.summary.matchedCount} of ${data.summary.totalExpectedHourlyPeriods} hourly periods` : undefined, description: 'Matched hourly periods as a percentage of expected hourly periods.' },
  ]

  return (
    <AppLayout
      reportingPeriod={formatRange(range.fromDate, range.toDate)}
      connection={health.connection}
      connectionDetail={health.detail}
      lastUpdated={fetchedAt ? formatUtcTime(fetchedAt) : null}
      refreshing={loading}
      onRefresh={refresh}
    >
      <Box sx={{ display: 'grid', gap: 3 }}>
        <DateRangeFilter applied={range} onApply={setRange} />
        <section id="overview" aria-label="Key metrics" style={{ scrollMarginTop: 88 }}>
          {error && <Box sx={{ mb: 2 }}><ErrorState error={error} onRetry={refresh} title="Could not load the evaluation" /></Box>}
          {data && !hasSamples && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              No matched hourly periods were found for this date range, so accuracy metrics are not available. Check the data coverage section for what was missing.
            </Alert>
          )}
          <Grid container spacing={2}>
            {kpis.map((kpi) => (
              <Grid key={kpi.label} size={{ xs: 6, sm: 4, lg: 3, xl: 'grow' }}>
                <KpiCard label={kpi.label} value={kpi.value} helper={error ? 'Unavailable' : kpi.helper} description={kpi.description} accent={kpi.accent} loading={loading} />
              </Grid>
            ))}
          </Grid>
        </section>
        <SectionCard id="chart" title="Actual vs day-ahead forecast" subtitle="Hourly matched periods, MW (UTC)">
          {loading && <LoadingState label="Loading chart data…" minHeight={280} />}
          {error && <ErrorState error={error} onRetry={refresh} />}
          {data && (
            <Suspense fallback={<LoadingState label="Loading chart…" minHeight={280} />}>
              <ActualForecastChart matchedData={data.matchedData} />
            </Suspense>
          )}
        </SectionCard>
        <SectionCard id="accuracy" title="Forecast accuracy" subtitle="Forecast error = forecast − actual">
          {loading && <LoadingState label="Loading accuracy metrics…" />}
          {error && <ErrorState error={error} onRetry={refresh} />}
          {data && <AccuracyMetrics evaluation={data} />}
        </SectionCard>
        <SectionCard id="coverage" title="Data coverage and quality" subtitle="Hourly forecast periods vs half-hourly actuals">
          {loading && <LoadingState label="Loading coverage details…" />}
          {error && <ErrorState error={error} onRetry={refresh} />}
          {data && <DataCoverage summary={data.summary} />}
        </SectionCard>
      </Box>
    </AppLayout>
  )
}
