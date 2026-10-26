import axios, { AxiosError, isCancel } from 'axios'

export const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

export function resolveBaseUrl(raw: string | undefined): string {
  const value = (raw ?? '').trim()
  return (value || DEFAULT_API_BASE_URL).replace(/\/+$/, '')
}

export const REQUEST_TIMEOUT_MS = 90_000

export const apiClient = axios.create({
  baseURL: resolveBaseUrl(import.meta.env.VITE_API_BASE_URL),
  timeout: REQUEST_TIMEOUT_MS,
  headers: { Accept: 'application/json' },
})

export type ApiErrorKind = 'network' | 'timeout' | 'http' | 'cancelled' | 'unknown'

/** Normalised error thrown by every service function. */
export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status?: number

  constructor(kind: ApiErrorKind, message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
  }
}

/** Extract a readable message from the backend's error bodies:
 *  FastAPI `{detail: string | [{msg}]}` and the custom `{message}` handlers. */
function messageFromBody(body: unknown): string | undefined {
  if (!body || typeof body !== 'object') return undefined
  const { detail, message } = body as { detail?: unknown; message?: unknown }
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : null))
      .filter((m): m is string => Boolean(m))
    if (parts.length) return parts.join('; ')
  }
  if (typeof message === 'string') return message
  return undefined
}

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  if (isCancel(error)) return new ApiError('cancelled', 'Request cancelled')
  if (error instanceof AxiosError) {
    if (error.response) {
      const { status, data } = error.response
      const fromBody = messageFromBody(data)
      return new ApiError('http', fromBody ?? `The server responded with HTTP ${status}.`, status)
    }
    if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
      return new ApiError('timeout', 'The request timed out. The backend may still be fetching data from Elexon.')
    }
    return new ApiError('network', `Cannot reach the API at ${apiClient.defaults.baseURL}.`)
  }
  return new ApiError('unknown', error instanceof Error ? error.message : 'Unexpected error')
}
