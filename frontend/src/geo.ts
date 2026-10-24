// California bounds from docs/api-contract.md: lat 32 to 42.1, lon -124.5 to -114. Outside this /api/point answers 422.
export function inCalifornia(lat: number, lon: number): boolean {
  return lat >= 32 && lat <= 42.1 && lon >= -124.5 && lon <= -114
}

export function haversineKm(a: [number, number], b: [number, number]): number {
  const rad = Math.PI / 180
  const dLat = (b[0] - a[0]) * rad
  const dLon = (b[1] - a[1]) * rad
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a[0] * rad) * Math.cos(b[0] * rad) * Math.sin(dLon / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(h))
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// "2025-07-30" -> "Jul 30 2025"
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  return `${MONTHS[m - 1]} ${d} ${y}`
}
