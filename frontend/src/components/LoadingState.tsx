import { Box, CircularProgress, Typography } from '@mui/material'

export default function LoadingState({ label = 'Loading data…', minHeight = 160 }: { label?: string; minHeight?: number }) {
  return (
    <Box role="status" aria-live="polite" sx={{ minHeight, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 1.5 }}>
      <CircularProgress size={28} />
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </Box>
  )
}
