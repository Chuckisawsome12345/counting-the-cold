import type { GridResponse } from '../client'

// Synthetic statewide grid for mock mode (VITE_USE_MOCK=1) so the chill layer can be built and checked without
// backend/data/grid/. A diagonal strip shaped roughly like the Central Valley, cooler (more chill) in the north.
// NOT real chill values: the real ones come from /api/grid.
const STEP = 0.25

export function mockGrid(season: number): GridResponse {
  const cells: GridResponse['cells'] = []
  for (let lat = 35.25; lat <= 40.25; lat += STEP) {
    const center = -121.9 + (40 - lat) * 0.62 // the valley runs south-east
    for (let lon = center - 0.75; lon <= center + 0.75; lon += STEP) {
      const ripple = Math.sin(lat * 7.3) * 2.2 + Math.cos(lon * 6.1) * 1.8
      cells.push({ lat: Math.round(lat * 100) / 100, lon: Math.round(lon * 100) / 100, value: Math.round((52 + (lat - 35) * 8 + ripple) * 10) / 10 })
    }
  }
  return {
    season: `${season}-${String(season + 1).slice(2)}`,
    metric: 'chill_portions',
    unit: 'CP',
    step_deg: STEP,
    built_at: '2026-10-24T02:00:00+00:00',
    cells,
  }
}
