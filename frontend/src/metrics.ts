import type { Metric, SeasonInfo } from './api/types'

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
    label: 'Utah Units',
    short: 'Utah',
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

