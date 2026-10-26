import { formatIsoDate, formatMW, formatNumber, formatPercent, formatSignedMW, formatUtcDateTime, parseIsoDate } from '../src/utils/formatters'

describe('formatters', () => {
  it('formats MW and percentages with grouping', () => {
    expect(formatMW(12345.678, 0)).toBe('12,346 MW')
    expect(formatMW(166.67)).toBe('166.7 MW')
    expect(formatPercent(8.333)).toBe('8.3%')
  })

  it('returns null for missing or invalid values', () => {
    expect(formatMW(null)).toBeNull()
    expect(formatMW(undefined)).toBeNull()
    expect(formatMW(Number.NaN)).toBeNull()
    expect(formatPercent(Infinity)).toBeNull()
    expect(formatNumber(null)).toBeNull()
    expect(formatSignedMW(null)).toBeNull()
  })

  it('signs bias values and does not sign a rounded zero', () => {
    expect(formatSignedMW(100)).toBe('+100.0 MW')
    expect(formatSignedMW(-4)).toBe('-4.0 MW')
    expect(formatSignedMW(0.01)).toBe('0.0 MW')
  })

  it('formats timestamps in UTC', () => {
    expect(formatUtcDateTime('2026-01-05T13:00:00Z')).toBe('05 Jan 2026, 13:00 UTC')
    expect(formatUtcDateTime('garbage')).toBe('—')
    expect(formatIsoDate('2026-01-01')).toBe('01 Jan 2026')
  })

  it('parses only valid calendar dates', () => {
    expect(parseIsoDate('2026-02-30')).toBeNull()
    expect(parseIsoDate('2026-1-1')).toBeNull()
    expect(parseIsoDate('2026-01-31')?.toISOString()).toBe('2026-01-31T00:00:00.000Z')
  })
})
