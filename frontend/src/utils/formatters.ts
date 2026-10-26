export const EM_DASH = '—'

export function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

const numberFormats = new Map<number, Intl.NumberFormat>()
function nf(decimals: number): Intl.NumberFormat {
  let f = numberFormats.get(decimals)
  if (!f) {
    f = new Intl.NumberFormat('en-GB', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    numberFormats.set(decimals, f)
  }
  return f
}

/** Plain number with thousands separators. Returns null for null/NaN/Infinity. */
export function formatNumber(value: number | null | undefined, decimals = 0): string | null {
  return isFiniteNumber(value) ? nf(decimals).format(value) : null
}

export function formatMW(value: number | null | undefined, decimals = 1): string | null {
  const n = formatNumber(value, decimals)
  return n === null ? null : `${n} MW`
}

/** Signed MW value, e.g. "+12.3 MW" / "-4.0 MW". */
export function formatSignedMW(value: number | null | undefined, decimals = 1): string | null {
  if (!isFiniteNumber(value)) return null
  const n = nf(decimals).format(Math.abs(value))
  const rounded = Number(Math.abs(value).toFixed(decimals))
  const sign = rounded === 0 ? '' : value > 0 ? '+' : '-'
  return `${sign}${n} MW`
}

export function formatPercent(value: number | null | undefined, decimals = 1): string | null {
  const n = formatNumber(value, decimals)
  return n === null ? null : `${n}%`
}

/** Format an ISO timestamp as "05 Jan 2026, 13:00 UTC". */
export function formatUtcDateTime(iso: string | null | undefined): string {
  if (!iso) return EM_DASH
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return EM_DASH
  const text = new Intl.DateTimeFormat('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'UTC',
  }).format(date)
  return `${text} UTC`
}

/** Format a YYYY-MM-DD string as "01 Jan 2026" without any local-timezone shifting. */
export function formatIsoDate(isoDate: string): string {
  const parsed = parseIsoDate(isoDate)
  if (!parsed) return isoDate
  return new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(parsed)
}

/** Strictly parse YYYY-MM-DD to a UTC midnight Date, or null if invalid (e.g. 2026-02-30). */
export function parseIsoDate(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return null
  const [y, m, d] = [Number(match[1]), Number(match[2]), Number(match[3])]
  const date = new Date(Date.UTC(y, m - 1, d))
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== m - 1 || date.getUTCDate() !== d) return null
  return date
}

export function formatRange(fromDate: string, toDate: string): string {
  return `${formatIsoDate(fromDate)} – ${formatIsoDate(toDate)} (UTC)`
}

/** Time of day for "last updated" labels, shown in UTC to stay consistent with the data. */
export function formatUtcTime(date: Date): string {
  return `${new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23', timeZone: 'UTC' }).format(date)} UTC`
}
