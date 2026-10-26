import type { ReactNode } from 'react'
import { Card, CardContent, Stack, Typography } from '@mui/material'

interface SectionCardProps {
  id?: string
  title: string
  subtitle?: string
  action?: ReactNode
  children: ReactNode
}

export default function SectionCard({ id, title, subtitle, action, children }: SectionCardProps) {
  const headingId = id ? `${id}-heading` : undefined
  return (
    <Card component="section" id={id} aria-labelledby={headingId} sx={{ scrollMarginTop: 88 }}>
      <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1}
          sx={{ mb: 2, justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' } }}
        >
          <div>
            <Typography id={headingId} variant="h2" component="h2">
              {title}
            </Typography>
            {subtitle && (
              <Typography variant="body2" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </div>
          {action}
        </Stack>
        {children}
      </CardContent>
    </Card>
  )
}
