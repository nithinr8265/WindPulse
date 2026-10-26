import type { AxiosAdapter, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios'
import { AxiosError } from 'axios'
import { apiClient, ApiError, resolveBaseUrl } from '../src/api/client'
import { getActuals, getEvaluation, getForecasts, getHealth } from '../src/api/windService'

let lastConfig: InternalAxiosRequestConfig | undefined
const originalAdapter = apiClient.defaults.adapter

function installAdapter(handler: (config: InternalAxiosRequestConfig) => Promise<unknown>) {
  apiClient.defaults.adapter = (async (config: InternalAxiosRequestConfig) => {
    lastConfig = config
    return handler(config)
  }) as AxiosAdapter
}

const ok = (config: AxiosRequestConfig, data: unknown) => ({ data, status: 200, statusText: 'OK', headers: {}, config })

afterEach(() => {
  apiClient.defaults.adapter = originalAdapter
  lastConfig = undefined
})

describe('resolveBaseUrl', () => {
  it('falls back to the local backend and strips trailing slashes', () => {
    expect(resolveBaseUrl(undefined)).toBe('http://127.0.0.1:8000')
    expect(resolveBaseUrl('  ')).toBe('http://127.0.0.1:8000')
    expect(resolveBaseUrl('http://api.test:9000//')).toBe('http://api.test:9000')
  })
})

describe('windService requests', () => {
  it('calls /health', async () => {
    installAdapter(async (c) => ok(c, { status: 'ok', app_name: 'x', timestamp: '2026-01-01T00:00:00Z', environment: 'dev' }))
    const res = await getHealth()
    expect(res.status).toBe('ok')
    expect(lastConfig?.url).toBe('/health')
  })

  it('maps evaluation params to the backend query names', async () => {
    installAdapter(async (c) => ok(c, {}))
    await getEvaluation({ fromDate: '2026-01-01', toDate: '2026-01-31', cutoffHour: 10, includeTimeseries: false })
    expect(lastConfig?.url).toBe('/api/v1/wind/evaluation')
    expect(lastConfig?.params).toEqual({
      from_date: '2026-01-01',
      to_date: '2026-01-31',
      cutoff_hour: 10,
      include_timeseries: false,
    })
  })

  it('maps actuals and forecasts params', async () => {
    installAdapter(async (c) => ok(c, {}))
    await getActuals({ fromDate: '2026-01-01', toDate: '2026-01-02', limit: 5 })
    expect(lastConfig?.url).toBe('/api/v1/wind/actuals')
    expect(lastConfig?.params).toMatchObject({ from_date: '2026-01-01', to_date: '2026-01-02', limit: 5 })
    await getForecasts({ fromDate: '2026-01-01', toDate: '2026-01-02' })
    expect(lastConfig?.url).toBe('/api/v1/wind/forecasts')
  })
})

describe('error normalisation', () => {
  function failWith(status: number, data: unknown) {
    installAdapter(async (c) => {
      throw new AxiosError('fail', 'ERR_BAD_RESPONSE', c, null, { data, status, statusText: '', headers: {}, config: c })
    })
  }

  it('uses FastAPI string detail', async () => {
    failWith(400, { detail: 'from_date must be before or equal to to_date' })
    await expect(getEvaluation({ fromDate: 'a', toDate: 'b' })).rejects.toMatchObject({
      kind: 'http',
      status: 400,
      message: 'from_date must be before or equal to to_date',
    })
  })

  it('uses validation-error detail arrays', async () => {
    failWith(422, { detail: [{ msg: 'String should match pattern' }] })
    await expect(getHealth()).rejects.toMatchObject({ status: 422, message: 'String should match pattern' })
  })

  it('uses the custom backend error body message', async () => {
    failWith(502, { status: 'error', error: 'ExternalServiceError', message: 'Elexon unavailable' })
    await expect(getHealth()).rejects.toMatchObject({ status: 502, message: 'Elexon unavailable' })
  })

  it('reports network failures', async () => {
    installAdapter(async (c) => {
      throw new AxiosError('Network Error', 'ERR_NETWORK', c)
    })
    const err = await getHealth().catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.kind).toBe('network')
  })

  it('reports timeouts', async () => {
    installAdapter(async (c) => {
      throw new AxiosError('timeout', 'ECONNABORTED', c)
    })
    await expect(getHealth()).rejects.toMatchObject({ kind: 'timeout' })
  })
})
