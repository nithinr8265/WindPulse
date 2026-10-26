import { AppBar, Box, Button, Chip, IconButton, Stack, Toolbar, Tooltip, Typography } from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import Refresh from '@mui/icons-material/Refresh'

export type ConnectionState = 'checking' | 'online' | 'offline'

interface HeaderProps {
  onMenuClick: () => void
  reportingPeriod: string
  connection: ConnectionState
  connectionDetail?: string
  lastUpdated: string | null
  refreshing: boolean
  onRefresh: () => void
}

const statusChip = {
  checking: { label: 'Checking API…', color: 'default' as const },
  online: { label: 'API connected', color: 'success' as const },
  offline: { label: 'API unreachable', color: 'error' as const },
}

export default function Header({
  onMenuClick,
  reportingPeriod,
  connection,
  connectionDetail,
  lastUpdated,
  refreshing,
  onRefresh,
}: HeaderProps) {
  const chip = statusChip[connection]
  return (
    <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}>
      <Toolbar sx={{ gap: 1.5, flexWrap: 'wrap', py: { xs: 1, md: 0 } }}>
        <IconButton edge="start" aria-label="Open navigation menu" onClick={onMenuClick} sx={{ display: { md: 'none' } }}>
          <MenuIcon />
        </IconButton>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h1" component="h1" noWrap>
            WindPulse Wind Analytics
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Reporting period: {reportingPeriod}
          </Typography>
        </Box>
        <Box sx={{ flexGrow: 1 }} />
        <Stack direction="row" spacing={1.5} useFlexGap sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
          <Tooltip title={connectionDetail ?? ''} arrow disableHoverListener={!connectionDetail}>
            <Chip size="small" variant="outlined" color={chip.color} label={chip.label} role="status" />
          </Tooltip>
          <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
            {lastUpdated ? `Last updated ${lastUpdated}` : 'Not yet refreshed'}
          </Typography>
          <Button variant="outlined" size="small" startIcon={<Refresh />} onClick={onRefresh} disabled={refreshing}>
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </Button>
        </Stack>
      </Toolbar>
    </AppBar>
  )
}
