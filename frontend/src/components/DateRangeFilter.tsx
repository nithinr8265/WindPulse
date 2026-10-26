import { useState } from 'react'
import { Alert, Box, Button, Stack, TextField, Typography } from '@mui/material'
import type { DateRangeParams } from '../types/wind'
import { DEFAULT_RANGE, LONG_RANGE_DAYS, validateRange } from '../utils/dateRange'

interface DateRangeFilterProps {
  applied: DateRangeParams
  onApply: (range: DateRangeParams) => void
  disabled?: boolean
}

export default function DateRangeFilter({ applied, onApply, disabled }: DateRangeFilterProps) {
  const [from, setFrom] = useState(applied.fromDate)
  const [to, setTo] = useState(applied.toDate)
  const validation = validateRange(from, to)
  const unchanged = from === applied.fromDate && to === applied.toDate
  const isDefault = applied.fromDate === DEFAULT_RANGE.fromDate && applied.toDate === DEFAULT_RANGE.toDate

  const apply = () => {
    if (validation.valid) onApply({ fromDate: from, toDate: to })
  }
  const reset = () => {
    setFrom(DEFAULT_RANGE.fromDate)
    setTo(DEFAULT_RANGE.toDate)
    onApply(DEFAULT_RANGE)
  }

  return (
    <Box
      component="form"
      aria-label="Evaluation date range"
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        apply()
      }}
      sx={{ bgcolor: 'background.paper', border: 1, borderColor: 'divider', borderRadius: 2, p: 2 }}
    >
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ alignItems: { sm: 'flex-start' } }}>
        <TextField
          label="From (UTC)"
          type="date"
          size="small"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          error={Boolean(validation.fromError)}
          helperText={validation.fromError ?? ' '}
          disabled={disabled}
          slotProps={{ inputLabel: { shrink: true }, htmlInput: { max: to || undefined } }}
        />
        <TextField
          label="To (UTC)"
          type="date"
          size="small"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          error={Boolean(validation.toError)}
          helperText={validation.toError ?? ' '}
          disabled={disabled}
          slotProps={{ inputLabel: { shrink: true }, htmlInput: { min: from || undefined } }}
        />
        <Stack direction="row" spacing={1} sx={{ pt: { sm: 0.25 } }}>
          <Button type="submit" variant="contained" disabled={disabled || !validation.valid || unchanged}>
            Apply range
          </Button>
          <Button type="button" variant="text" onClick={reset} disabled={disabled || (isDefault && unchanged)}>
            Reset to January 2026
          </Button>
        </Stack>
      </Stack>
      {validation.rangeError && (
        <Alert severity="error" sx={{ mt: 1 }} role="alert">
          {validation.rangeError}
        </Alert>
      )}
      {validation.valid && validation.days !== null && validation.days > LONG_RANGE_DAYS && (
        <Alert severity="info" sx={{ mt: 1 }}>
          This range covers {validation.days} days. The backend fetches data from Elexon for every request, so loading may be slow.
        </Alert>
      )}
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
        Dates are UTC calendar days (inclusive) and are sent to the evaluation endpoint as from_date and to_date. The KPIs, chart, accuracy and coverage sections all use this range.
      </Typography>
    </Box>
  )
}
