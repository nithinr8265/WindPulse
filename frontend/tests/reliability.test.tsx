import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import App from '../src/App'
import ErrorBoundary from '../src/components/ErrorBoundary'
import * as service from '../src/api/windService'
import { makeEvaluation, makeMatched } from './fixtures'

vi.mock('../src/api/windService', () => ({ getHealth: vi.fn(), getEvaluation: vi.fn() }))

beforeEach(() => {
  vi.mocked(service.getHealth).mockResolvedValue({ status: 'ok', app_name: 'x', timestamp: '2026-01-01T00:00:00Z', environment: 'test' })
})
afterEach(() => vi.clearAllMocks())

describe('stale responses', () => {
  it('ignores a slow earlier response that arrives after a newer range was loaded', async () => {
    let resolveSlow: (v: ReturnType<typeof makeEvaluation>) => void = () => undefined
    const slow = new Promise<ReturnType<typeof makeEvaluation>>((r) => (resolveSlow = r))
    const fresh = makeEvaluation()
    fresh.metrics.meanActualMW = 4321
    vi.mocked(service.getEvaluation).mockReturnValueOnce(slow).mockResolvedValue(fresh)

    render(<App />)
    fireEvent.change(screen.getByLabelText('To (UTC)'), { target: { value: '2026-01-15' } })
    await userEvent.click(screen.getByRole('button', { name: 'Apply range' }))
    expect(await screen.findByText('4,321 MW')).toBeInTheDocument()

    const stale = makeEvaluation()
    stale.metrics.meanActualMW = 1111
    await act(async () => resolveSlow(stale))
    expect(screen.getByText('4,321 MW')).toBeInTheDocument()
    expect(screen.queryByText('1,111 MW')).not.toBeInTheDocument()
  })
})

describe('chart with missing periods', () => {
  it('still renders with gaps in matched data', async () => {
    vi.mocked(service.getEvaluation).mockResolvedValue(makeEvaluation({ matchedData: [makeMatched(0, 1, 2), makeMatched(9, 3, 4)] }))
    render(<App />)
    expect(await screen.findByRole('img', { name: /2 matched hourly periods/ })).toBeInTheDocument()
    expect(await screen.findByText(/Lines break at 1 gap/)).toBeInTheDocument()
  })
})

describe('ErrorBoundary', () => {
  it('shows a recoverable message instead of a blank page', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    function Boom(): never {
      throw new Error('boom')
    }
    render(<ErrorBoundary><Boom /></ErrorBoundary>)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    spy.mockRestore()
  })
})
