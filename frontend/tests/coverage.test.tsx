import { render, screen } from '@testing-library/react'
import DataCoverage, { coverageWarnings } from '../src/components/DataCoverage'
import { makeEvaluation } from './fixtures'

const base = makeEvaluation().summary

describe('coverageWarnings', () => {
  it('flags incomplete coverage and missing records from the backend counts', () => {
    const text = coverageWarnings(base).map((w) => w.message).join('\n')
    expect(text).toMatch(/Coverage is incomplete: 3 of 744/)
    expect(text).toMatch(/44 expected hourly period\(s\) have no eligible day-ahead forecast/)
    expect(text).toMatch(/2 expected hourly period\(s\) have a forecast but no actual/)
  })

  it('still reports unmatched half-hourly actuals at 100% hourly coverage', () => {
    const full = { ...base, coveragePercentage: 100, matchedCount: 744, missingHourlyForecastCount: 0, missingHourlyActualCount: 0 }
    const warnings = coverageWarnings(full)
    expect(warnings).toHaveLength(1)
    expect(warnings[0].severity).toBe('info')
    expect(warnings[0].message).toMatch(/744 half-hourly actual record\(s\)/)
    expect(warnings[0].message).toMatch(/even when hourly coverage is 100%/)
  })

  it('has nothing to flag when there are no gaps and no unmatched actuals', () => {
    expect(coverageWarnings({ ...base, coveragePercentage: 100, missingHourlyForecastCount: 0, missingHourlyActualCount: 0, unmatchedHalfHourlyActualsCount: 0 })).toEqual([])
  })
})

describe('DataCoverage', () => {
  it('keeps hourly, half-hourly and revision counts as separate labelled figures', () => {
    render(<DataCoverage summary={base} />)
    for (const label of ['Expected hourly periods', 'Raw forecast revisions', 'Eligible forecasts', 'Matched hourly periods', 'Missing hourly forecasts', 'Missing hourly actuals', 'Expected half-hourly periods', 'Actual records retrieved', 'Unmatched half-hourly actuals']) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
    expect(screen.getByText('5,000')).toBeInTheDocument() // raw revisions, not a sample count
    expect(screen.getByRole('progressbar', { name: 'Hourly forecast coverage' })).toHaveAttribute('aria-valuenow', '94.09')
  })
})
