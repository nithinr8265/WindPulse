import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import App from '../src/App'
import DateRangeFilter from '../src/components/DateRangeFilter'
import * as service from '../src/api/windService'
import { makeEvaluation } from './fixtures'

vi.mock('../src/api/windService', () => ({ getHealth: vi.fn(), getEvaluation: vi.fn() }))

const range = { fromDate: '2026-01-01', toDate: '2026-01-31' }

describe('DateRangeFilter', () => {
  it('prevents applying an invalid range', () => {
    const onApply = vi.fn()
    render(<DateRangeFilter applied={range} onApply={onApply} />)
    fireEvent.change(screen.getByLabelText('From (UTC)'), { target: { value: '2026-02-10' } })
    expect(screen.getByRole('alert')).toHaveTextContent(/start date must be on or before the end date/i)
    expect(screen.getByRole('button', { name: 'Apply range' })).toBeDisabled()
    expect(onApply).not.toHaveBeenCalled()
  })

  it('applies a valid range exactly as entered (UTC calendar days)', async () => {
    const onApply = vi.fn()
    render(<DateRangeFilter applied={range} onApply={onApply} />)
    fireEvent.change(screen.getByLabelText('To (UTC)'), { target: { value: '2026-01-15' } })
    await userEvent.click(screen.getByRole('button', { name: 'Apply range' }))
    expect(onApply).toHaveBeenCalledWith({ fromDate: '2026-01-01', toDate: '2026-01-15' })
  })
})

describe('dashboard date filtering', () => {
  beforeEach(() => {
    vi.mocked(service.getHealth).mockResolvedValue({ status: 'ok', app_name: 'x', timestamp: '2026-01-01T00:00:00Z', environment: 'test' })
    vi.mocked(service.getEvaluation).mockResolvedValue(makeEvaluation())
  })
  afterEach(() => vi.clearAllMocks())

  it('starts on January 2026 and reloads with the new range from the backend', async () => {
    render(<App />)
    await screen.findByText('2,000 MW')
    expect(service.getEvaluation).toHaveBeenLastCalledWith(expect.objectContaining({ fromDate: '2026-01-01', toDate: '2026-01-31' }), expect.anything())

    fireEvent.change(screen.getByLabelText('From (UTC)'), { target: { value: '2026-01-10' } })
    fireEvent.change(screen.getByLabelText('To (UTC)'), { target: { value: '2026-01-12' } })
    await userEvent.click(screen.getByRole('button', { name: 'Apply range' }))

    await waitFor(() =>
      expect(service.getEvaluation).toHaveBeenLastCalledWith(expect.objectContaining({ fromDate: '2026-01-10', toDate: '2026-01-12' }), expect.anything()),
    )
    expect(await screen.findByText(/10 Jan 2026 – 12 Jan 2026 \(UTC\)/)).toBeInTheDocument()
  })
})
