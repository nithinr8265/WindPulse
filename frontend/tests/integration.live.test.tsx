/**
 * Opt-in integration checks against a RUNNING backend (default http://127.0.0.1:8000).
 * Skipped unless VITE_RUN_LIVE_API_TESTS=1, so `npm test` stays hermetic.
 *   PowerShell: $env:VITE_RUN_LIVE_API_TESTS="1"; npm test
 *   bash:       VITE_RUN_LIVE_API_TESTS=1 npm test
 */
import { render, screen } from '@testing-library/react'
import App from '../src/App'
import { ApiError } from '../src/api/client'
import { getEvaluation, getHealth } from '../src/api/windService'

const live = import.meta.env.VITE_RUN_LIVE_API_TESTS === '1'

describe.skipIf(!live)('live backend integration', () => {
  it('health check responds ok', async () => {
    const health = await getHealth()
    expect(health.status).toBe('ok')
  })

  it('evaluation matches the typed contract and internal consistency rules', async () => {
    const ev = await getEvaluation({ fromDate: '2026-01-01', toDate: '2026-01-31' })
    const s = ev.summary
    expect(s.totalExpectedHourlyPeriods).toBe(744)
    expect(s.totalActualHalfHourlyPeriods).toBe(1488)
    expect(ev.matchedData).toHaveLength(s.matchedCount)
    expect(ev.metrics.sampleCount).toBe(s.matchedCount)
    expect(s.coveragePercentage).toBeCloseTo((s.matchedCount / s.totalExpectedHourlyPeriods) * 100, 1)
    for (const key of ['maeMW', 'rmseMW', 'biasMW', 'meanActualMW', 'meanForecastMW'] as const) {
      expect(typeof ev.metrics[key]).toBe('number')
    }
    const first = ev.matchedData[0]
    expect(first.errorMW).toBeCloseTo(first.forecastGenerationMW - first.actualGenerationMW, 1)
    expect(new Date(first.forecastPublishTime) <= new Date(first.decisionCutoffTime)).toBe(true)
  }, 40_000)

  it('supports include_timeseries=false', async () => {
    const ev = await getEvaluation({ fromDate: '2026-01-01', toDate: '2026-01-02', includeTimeseries: false })
    expect(ev.matchedData).toEqual([])
    expect(ev.summary.totalExpectedHourlyPeriods).toBe(48)
  })

  it('surfaces backend validation errors as ApiError', async () => {
    const err = await getEvaluation({ fromDate: '2026-02-01', toDate: '2026-01-01' }).catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(400)
    expect(err.message).toMatch(/must be before or equal/)
  })

  it('renders the dashboard with the backend values', async () => {
    const ev = await getEvaluation({ fromDate: '2026-01-01', toDate: '2026-01-31' })
    render(<App />)
    const expected = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 }).format(ev.metrics.meanActualMW)
    expect(await screen.findByText(`${expected} MW`, {}, { timeout: 30_000 })).toBeInTheDocument()
    expect(await screen.findByText('API connected')).toBeInTheDocument()
  }, 40_000)
})
