import { validateRange } from '../src/utils/dateRange'

describe('validateRange', () => {
  it('accepts a valid range and counts inclusive days', () => {
    const v = validateRange('2026-01-01', '2026-01-31')
    expect(v.valid).toBe(true)
    expect(v.days).toBe(31)
  })

  it('accepts a single day', () => {
    expect(validateRange('2026-01-05', '2026-01-05')).toMatchObject({ valid: true, days: 1 })
  })

  it('rejects start after end', () => {
    const v = validateRange('2026-02-01', '2026-01-31')
    expect(v.valid).toBe(false)
    expect(v.rangeError).toMatch(/on or before/)
  })

  it('rejects empty and impossible dates', () => {
    expect(validateRange('', '2026-01-31').fromError).toMatch(/required/)
    expect(validateRange('2026-01-01', '').toError).toMatch(/required/)
    expect(validateRange('2026-02-30', '2026-03-01').valid).toBe(false)
  })
})
