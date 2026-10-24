const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// 87.5 -> "87.5", 1183 -> "1,183". `digits` is the most decimals shown; trailing zeros are kept off whole numbers.
export function formatNumber(value: number, digits = 0): string {
  return value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: digits })
}

// Metric value with a fixed number of decimals (87.5, not 88), thousands separators.
export function formatFixed(value: number, digits: number): string {
  return value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

// "2026-09-01" -> "Sep 1"
export function formatMonthDay(iso: string): string {
  const [, m, d] = iso.split('-').map(Number)
  return `${MONTHS[m - 1]} ${d}`
}

export function median(values: number[]): number | null {
  if (!values.length) return null
  const s = [...values].sort((a, b) => a - b)
  const mid = Math.floor(s.length / 2)
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2
}

// Days from Sep 1 of the season's start year to `asOf` (0-based, like history[].cumulative[].day).
export function dayOfSeason(seasonLabel: string, asOf: string): number {
  const startYear = Number(seasonLabel.slice(0, 4))
  const [y, m, d] = asOf.split('-').map(Number)
  return Math.round((Date.UTC(y, m - 1, d) - Date.UTC(startYear, 8, 1)) / 86_400_000)
}
