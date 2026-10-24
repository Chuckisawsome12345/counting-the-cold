import type { Metric, PointResponse, SeasonInfo } from './api/types'

export interface MetricInfo {
  metric: Metric
  label: string // card and chart title
  short: string // short tab label on phones
  unit: string // card header and chart axis
  footUnit: string // "± 2 CP expected"
  digits: number // decimals shown
  accent: 'cold' | 'heat'
  startField: keyof Pick<SeasonInfo, 'portions_start' | 'hours_start' | 'gdd_start'>
  startText: (monthDay: string) => string // shown while the metric has nothing counted yet
}

// The four metrics, in card order. Chill is cold-ramp, GDD is heat-ramp.
export const METRICS: MetricInfo[] = [
  {
    metric: 'chill_portions',
    label: 'Chill Portions',
    short: 'CP',
    unit: 'portions',
    footUnit: 'CP',
    digits: 1,
    accent: 'cold',
    startField: 'portions_start',
    startText: (d) => `counting since ${d}`,
  },
  {
    metric: 'chill_hours',
    label: 'Chill Hours',
    short: 'Hours',
    unit: 'h',
    footUnit: 'h',
    digits: 0,
    accent: 'cold',
    startField: 'hours_start',
    startText: (d) => `counts from ${d}`,
  },
  {
    metric: 'utah_units',
    label: 'Chill Units',
    short: 'CU',
    unit: 'CU',
    footUnit: 'CU',
    digits: 0,
    accent: 'cold',
    startField: 'hours_start',
    startText: (d) => `counts from ${d}`,
  },
  {
    metric: 'gdd',
    label: 'Growing Degree Days',
    short: 'GDD',
    unit: '°F-days',
    footUnit: '°F-days',
    digits: 0,
    accent: 'heat',
    startField: 'gdd_start',
    startText: (d) => `counts from ${d}`,
  },
]


// True when a measure has no data at all: zero now and zero in every one of the 10 past seasons. A real orchard never
// has that (chill portions, for one, accumulate every winter), so it means the data service is not calculating the
// measure yet, and the UI says so instead of drawing a flat line of zeros.
export function isUnavailable(data: PointResponse, metric: Metric): boolean {
  if (data.totals[metric] !== 0) return false
  if (data.history.some((h) => h.totals[metric] !== 0)) return false
  return !data.forecast?.daily.some((d) => d[metric] !== 0)
}

// The measure to open on: the first one that has data, so the page never greets anyone with an empty chart.
export function firstAvailable(data: PointResponse): Metric {
  return METRICS.find((m) => !isUnavailable(data, m.metric))?.metric ?? METRICS[0].metric
}
