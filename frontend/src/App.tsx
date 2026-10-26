import { CssBaseline, ThemeProvider } from '@mui/material'
import { theme } from './theme'
import DashboardPage from './pages/DashboardPage'
import ErrorBoundary from './components/ErrorBoundary'

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ErrorBoundary>
        <DashboardPage />
      </ErrorBoundary>
    </ThemeProvider>
  )
}
