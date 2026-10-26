import { createTheme } from '@mui/material/styles'

export const palette = {
  navy: '#0f1b2d',
  navyLight: '#1a2a42',
  background: '#f4f6f9',
  border: '#e2e8f0',
  actual: '#059669', // green: actual generation
  forecast: '#2563eb', // blue: forecasts
  warning: '#d97706', // amber
  error: '#dc2626', // red
  text: '#0f172a',
  muted: '#64748b',
}

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: palette.forecast },
    success: { main: palette.actual },
    warning: { main: palette.warning },
    error: { main: palette.error },
    background: { default: palette.background, paper: '#ffffff' },
    text: { primary: palette.text, secondary: palette.muted },
    divider: palette.border,
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: '"Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    h1: { fontSize: '1.25rem', fontWeight: 700 },
    h2: { fontSize: '1.05rem', fontWeight: 650 },
    h3: { fontSize: '0.95rem', fontWeight: 650 },
    overline: { letterSpacing: '0.08em', fontWeight: 600 },
  },
  components: {
    MuiCard: {
      defaultProps: { variant: 'outlined' },
      styleOverrides: { root: { boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)' } },
    },
    MuiButton: { styleOverrides: { root: { textTransform: 'none', fontWeight: 600 } } },
  },
})
