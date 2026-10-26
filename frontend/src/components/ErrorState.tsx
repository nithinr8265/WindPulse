import { Alert, AlertTitle, Button } from '@mui/material'
import type { ApiError } from '../api/client'

interface ErrorStateProps {
  error: ApiError
  onRetry?: () => void
  title?: string
}

function hint(error: ApiError): string | null {
  switch (error.kind) {
    case 'network':
      return 'Check that the FastAPI backend is running and that VITE_API_BASE_URL points to it.'
    case 'timeout':
      return 'The backend fetches data from Elexon on each request, which can be slow. Try again or choose a shorter date range.'
    case 'http':
      return error.status !== undefined && error.status >= 500
        ? 'The backend or the upstream Elexon service returned an error. Retrying may help.'
        : null
    default:
      return null
  }
}

export default function ErrorState({ error, onRetry, title = 'Could not load data' }: ErrorStateProps) {
  const extra = hint(error)
  return (
    <Alert
      severity="error"
      action={
        onRetry && (
          <Button color="inherit" size="small" onClick={onRetry}>
            Retry
          </Button>
        )
      }
    >
      <AlertTitle>{title}</AlertTitle>
      {error.message}
      {extra && <div style={{ marginTop: 4 }}>{extra}</div>}
    </Alert>
  )
}
