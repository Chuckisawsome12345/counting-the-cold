import type { GridResponse } from './api/client'

// Low to high chill: pale ice to deep blue. Chosen to stay visible on both the light and the dark map tiles.
export const CHILL_RAMP = [
  [159, 227, 255],
  [79, 180, 240],
  [29, 95, 176],
]

export function chillColour(t: number): string {
  const x = Math.min(1, Math.max(0, t)) * (CHILL_RAMP.length - 1)
  const i = Math.min(CHILL_RAMP.length - 2, Math.floor(x))
  const [a, b] = [CHILL_RAMP[i], CHILL_RAMP[i + 1]]
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * (x - i))).join(',')})`
}

export function gridRange(grid: GridResponse): [number, number] {
  const values = grid.cells.map((c) => c.value)
  return [Math.min(...values), Math.max(...values)]
}
