import type { Metric, MetricError, StationValidation, Totals, ValidationResponse } from '../types'

// Synthetic validation results for mock mode (VITE_USE_MOCK=1), so the accuracy tab can be built and checked
// without backend/data/validation.json. NOT real results: the real ones come from /api/validation.
const METRIC_SCALE: Record<Metric, number> = { chill_portions: 1, chill_hours: 11, utah_units: 14, gdd: 13 }
const METRICS = Object.keys(METRIC_SCALE) as Metric[]

// id, name, seasons tested, raw error and corrected error in chill portions
const FIXTURE: [number, string, number, number, number][] = [
  [12, 'Durham', 10, 5.1, 1.6],
  [6, 'Davis', 10, 3.4, 1.8],
  [70, 'Manteca', 8, 3.8, 2.0],
  [71, 'Modesto', 9, 4.0, 2.1],
  [39, 'Parlier', 10, 4.6, 2.2],
  [5, 'Shafter', 7, 5.3, 2.4],
  [244, 'Biggs', 6, 4.1, 1.7],
  [250, 'Williams', 6, 3.9, 1.8],
  [222, 'Gerber South', 5, 3.7, 1.5],
]

const round1 = (n: number) => Math.round(n * 10) / 10

function maeFor(raw: number, corrected: number): Partial<Record<Metric, MetricError>> {
  return Object.fromEntries(
    METRICS.map((m) => [m, { raw_mae: round1(raw * METRIC_SCALE[m]), corrected_mae: round1(corrected * METRIC_SCALE[m]) }]),
  )
}

function totals(base: number, offset: number): Totals {
  return Object.fromEntries(METRICS.map((m) => [m, round1((base + offset) * METRIC_SCALE[m])])) as unknown as Totals
}

const stations: StationValidation[] = FIXTURE.map(([id, name, n, raw, corrected]) => ({
  id,
  name,
  mae: maeFor(raw, corrected),
  seasons: Array.from({ length: n }, (_, i) => ({
    season: `${2024 - i}-${String(2025 - i).slice(2)}`,
    cimis: totals(60, 0),
    raw: totals(60, raw),
    corrected: totals(60, corrected),
  })),
}))

export const MOCK_VALIDATION: ValidationResponse = {
  built_at: '2026-10-24T03:00:00',
  summary: Object.fromEntries(
    METRICS.map((m) => {
      const mean = (pick: (e: MetricError) => number) =>
        round1(stations.reduce((sum, s) => sum + pick(s.mae[m] as MetricError), 0) / stations.length)
      return [m, { raw_mae: mean((e) => e.raw_mae), corrected_mae: mean((e) => e.corrected_mae) }]
    }),
  ),
  stations,
}
