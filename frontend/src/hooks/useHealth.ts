import { useEffect, useState } from 'react'
import { getHealth } from '../api/windService'
import { toApiError } from '../api/client'
import type { ConnectionState } from '../components/Header'

export const HEALTH_POLL_INTERVAL_MS = 30_000

export interface HealthState {
  connection: ConnectionState
  detail?: string
}

/** Real /health check: on mount, on every manual refresh, and on a slow poll. */
export function useHealth(refreshToken: number): HealthState {
  const [state, setState] = useState<HealthState & { token: number }>({ connection: 'checking', token: -1 })

  useEffect(() => {
    let active = true
    const controller = new AbortController()

    const check = () => {
      getHealth(controller.signal)
        .then((h) => {
          if (active) setState({ token: refreshToken, connection: 'online', detail: `${h.app_name} (${h.environment})` })
        })
        .catch((e: unknown) => {
          const error = toApiError(e)
          if (active && error.kind !== 'cancelled') setState({ token: refreshToken, connection: 'offline', detail: error.message })
        })
    }

    check()
    const timer = window.setInterval(check, HEALTH_POLL_INTERVAL_MS)
    return () => {
      active = false
      controller.abort()
      window.clearInterval(timer)
    }
  }, [refreshToken])

  // Until the check for the current refresh completes, keep the previous result visible
  // after the first load, but show "checking" on the very first request.
  return { connection: state.connection, detail: state.detail }
}
