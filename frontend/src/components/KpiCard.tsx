import { Card, CardContent, Skeleton, Tooltip, Typography } from '@mui/material'
import InfoOutlined from '@mui/icons-material/InfoOutlined'

interface KpiCardProps {
  label: string
  /** Pre-formatted value, e.g. "1,234 MW". Use null while no data is available. */
  value: string | null
  helper?: string
  /** Longer explanation shown in a tooltip. */
  description?: string
  accent?: string
  loading?: boolean
}

export default function KpiCard({ label, value, helper, description, accent = '#64748b', loading }: KpiCardProps) {
  return (
    <Card role="group" aria-label={label} sx={{ height: '100%', borderTop: `3px solid ${accent}` }}>
      <CardContent sx={{ p: 2 }}>
        <Typography variant="overline" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          {label}
          {description && (
            <Tooltip title={description} arrow enterTouchDelay={0}>
              <span tabIndex={0} role="img" aria-label={`About ${label}: ${description}`} style={{ display: 'inline-flex' }}>
                <InfoOutlined sx={{ fontSize: 14 }} />
              </span>
            </Tooltip>
          )}
        </Typography>
        {loading ? (
          <Skeleton variant="text" width="70%" sx={{ fontSize: '1.75rem' }} />
        ) : (
          <Typography variant="h5" component="p" sx={{ fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>
            {value ?? '—'}
          </Typography>
        )}
        {helper && (
          <Typography variant="caption" color="text.secondary">
            {helper}
          </Typography>
        )}
      </CardContent>
    </Card>
  )
}
