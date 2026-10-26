import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import App from '../src/App'
import { ApiError } from '../src/api/client'
import * as service from '../src/api/windService'
import { makeEvaluation } from './fixtures'

vi.mock('../src/api/windService', () => ({ getHealth: vi.fn(), getEvaluation: vi.fn() }))

const health = { status: 'ok', app_name: 'WindPulse API', timestamp: '2026-01-01T00:00:00Z', environment: 'test' }

beforeEach(() => {
  vi.mocked(service.getHealth).mockResolvedValue(health)
})
afterEach(() => vi.clearAllMocks())

function kpi(label: string) {
  return screen.getByRole('group', { name: label })
}

describe('live KPI cards', () => {
  it('shows values from the evaluation response', async () => {
    vi.mocked(service.getEvaluation).mockResolvedValue(makeEvaluation())
    render(<App />)
    expect(await screen.findByText('2,000 MW')).toBeInTheDocument() // mean actual
    expect(within(kpi('Mean forecast')).getByText('2,100 MW')).toBeInTheDocument()
    expect(within(kpi('MAE')).getByText('166.7 MW')).toBeInTheDocument()
    expect(within(kpi('RMSE')).getByText('182.6 MW')).toBeInTheDocument()
    expect(within(kpi('Bias')).getByText('+100.0 MW')).toBeInTheDocument()
    expect(within(kpi('Bias')).getByText('Over-forecasting on average')).toBeInTheDocument()
    expect(within(kpi('nMAE')).getByText('8.3%')).toBeInTheDocument()
    expect(within(kpi('Coverage')).getByText('94.1%')).toBeInTheDocument()
    expect(await screen.findByText('API connected')).toBeInTheDocument()
    expect(service.getEvaluation).toHaveBeenCalledWith(
      expect.objectContaining({ fromDate: '2026-01-01', toDate: '2026-01-31' }),
      expect.any(AbortSignal),
    )
  })

  it('does not present zero-sample metrics as real values', async () => {
    const base = makeEvaluation()
    vi.mocked(service.getEvaluation).mockResolvedValue(
      makeEvaluation({
        matchedData: [],
        summary: { ...base.summary, matchedCount: 0, coveragePercentage: 0 },
        metrics: { ...base.metrics, sampleCount: 0, maeMW: 0, rmseMW: 0, biasMW: 0, nmaePercentage: null, mapePercentage: null, meanActualMW: 0, meanForecastMW: 0 },
      }),
    )
    render(<App />)
    expect(await screen.findByText(/No matched hourly periods were found/)).toBeInTheDocument()
    expect(within(kpi('MAE')).getByText('—')).toBeInTheDocument()
    expect(within(kpi('Mean actual')).getByText('—')).toBeInTheDocument()
  })

  it('shows an error state and retries', async () => {
    vi.mocked(service.getEvaluation).mockRejectedValueOnce(new ApiError('network', 'Cannot reach the API at http://127.0.0.1:8000.'))
    render(<App />)
    expect(await screen.findAllByText(/Cannot reach the API/)).not.toHaveLength(0)
    vi.mocked(service.getEvaluation).mockResolvedValue(makeEvaluation())
    await userEvent.click(screen.getAllByRole('button', { name: 'Retry' })[0])
    expect(await screen.findByText('2,000 MW')).toBeInTheDocument()
  })

  it('reports an unreachable backend in the header from the health check', async () => {
    vi.mocked(service.getHealth).mockRejectedValue(new ApiError('network', 'down'))
    vi.mocked(service.getEvaluation).mockResolvedValue(makeEvaluation())
    render(<App />)
    expect(await screen.findByText('API unreachable')).toBeInTheDocument()
  })
})

describe('actual vs forecast chart section', () => {
  it('describes the plotted real data and shows an empty message when nothing matched', async () => {
    vi.mocked(service.getEvaluation).mockResolvedValue(makeEvaluation())
    const { unmount } = render(<App />)
    expect(await screen.findByRole('img', { name: /3 matched hourly periods/ })).toBeInTheDocument()
    unmount()

    vi.mocked(service.getEvaluation).mockResolvedValue(makeEvaluation({ matchedData: [] }))
    render(<App />)
    expect(await screen.findByText(/No matched hourly periods to plot/)).toBeInTheDocument()
  })
})
