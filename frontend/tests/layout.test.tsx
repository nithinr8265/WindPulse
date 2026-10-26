import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import App from '../src/App'
import { ApiError } from '../src/api/client'

vi.mock('../src/api/windService', () => ({
  getHealth: vi.fn(() => Promise.reject(new ApiError('network', 'down'))),
  getEvaluation: vi.fn(() => Promise.reject(new ApiError('network', 'down'))),
}))

describe('dashboard layout', () => {
  it('renders the app shell with navigation and refresh control', async () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: 'WindPulse Wind Analytics' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Dashboard sections' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /refresh/i })).toBeInTheDocument()
    expect(await screen.findByText('API unreachable')).toBeInTheDocument()
  })
})
