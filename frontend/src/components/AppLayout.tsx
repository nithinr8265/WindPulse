import { useState, type ReactNode } from 'react'
import { Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText, Typography } from '@mui/material'
import AirIcon from '@mui/icons-material/Air'
import SpeedIcon from '@mui/icons-material/Speed'
import ShowChart from '@mui/icons-material/ShowChart'
import FactCheck from '@mui/icons-material/FactCheck'
import StorageIcon from '@mui/icons-material/Storage'
import { palette } from '../theme'
import Header, { type ConnectionState } from './Header'

const DRAWER_WIDTH = 248

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: <SpeedIcon fontSize="small" /> },
  { id: 'chart', label: 'Actual vs forecast', icon: <ShowChart fontSize="small" /> },
  { id: 'accuracy', label: 'Forecast accuracy', icon: <FactCheck fontSize="small" /> },
  { id: 'coverage', label: 'Data coverage', icon: <StorageIcon fontSize="small" /> },
]

interface AppLayoutProps {
  children: ReactNode
  reportingPeriod: string
  connection: ConnectionState
  connectionDetail?: string
  lastUpdated: string | null
  refreshing: boolean
  onRefresh: () => void
}

function NavContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Box sx={{ color: '#cbd5e1', height: '100%' }} component="nav" aria-label="Dashboard sections">
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, px: 2.5, py: 2.5 }}>
        <AirIcon sx={{ color: '#34d399' }} />
        <Box>
          <Typography sx={{ color: '#fff', fontWeight: 700, lineHeight: 1.1 }}>WindPulse</Typography>
          <Typography variant="caption" sx={{ color: '#94a3b8' }}>
            Wind Analytics
          </Typography>
        </Box>
      </Box>
      <List sx={{ px: 1.5 }}>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.id}
            component="a"
            href={`#${item.id}`}
            onClick={onNavigate}
            sx={{ borderRadius: 1.5, mb: 0.5, '&:hover': { bgcolor: palette.navyLight }, '&:focus-visible': { outline: '2px solid #60a5fa' } }}
          >
            <ListItemIcon sx={{ minWidth: 34, color: 'inherit' }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} slotProps={{ primary: { sx: { fontSize: 14 } } }} />
          </ListItemButton>
        ))}
      </List>
      <Typography variant="caption" sx={{ display: 'block', px: 2.5, mt: 3, color: '#64748b' }}>
        Day-ahead wind forecast evaluation for UK purchasing decisions. Data: Elexon BMRS (FUELHH, WINDFOR). All times UTC.
      </Typography>
    </Box>
  )
}

export default function AppLayout({ children, ...headerProps }: AppLayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Box
        component="a"
        href="#main-content"
        sx={{
          position: 'absolute', left: -9999, top: 8, zIndex: 2000, bgcolor: '#fff', px: 2, py: 1, borderRadius: 1,
          '&:focus': { left: 8 },
        }}
      >
        Skip to main content
      </Box>
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{ display: { xs: 'block', md: 'none' }, '& .MuiDrawer-paper': { width: DRAWER_WIDTH, bgcolor: palette.navy, boxSizing: 'border-box' } }}
      >
        <NavContent onNavigate={() => setMobileOpen(false)} />
      </Drawer>
      <Drawer
        variant="permanent"
        open
        sx={{
          display: { xs: 'none', md: 'block' }, width: DRAWER_WIDTH, flexShrink: 0,
          '& .MuiDrawer-paper': { width: DRAWER_WIDTH, bgcolor: palette.navy, boxSizing: 'border-box', borderRight: 0 },
        }}
      >
        <NavContent />
      </Drawer>
      <Box sx={{ flexGrow: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <Header onMenuClick={() => setMobileOpen(true)} {...headerProps} />
        <Box component="main" id="main-content" tabIndex={-1} sx={{ p: { xs: 2, md: 3 }, maxWidth: 1400, width: '100%', mx: 'auto', outline: 'none' }}>
          {children}
        </Box>
      </Box>
    </Box>
  )
}
