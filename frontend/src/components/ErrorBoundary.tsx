import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Alert, AlertTitle, Box, Button } from '@mui/material'

interface State {
  failed: boolean
}

/** Last-resort guard so an unexpected rendering error shows a recoverable message, not a blank page. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled UI error', error, info.componentStack)
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <Box sx={{ p: 3, maxWidth: 640, mx: 'auto' }}>
        <Alert severity="error" action={<Button color="inherit" size="small" onClick={() => window.location.reload()}>Reload</Button>}>
          <AlertTitle>Something went wrong</AlertTitle>
          The dashboard hit an unexpected error. Reload the page to try again.
        </Alert>
      </Box>
    )
  }
}
