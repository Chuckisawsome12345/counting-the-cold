import type { Metric, PointResponse } from './api/types'
import { dayOfSeason, median } from './format'

// One row per day of the season (day 0 = Sep 1). Past seasons are h0..h9, oldest first.
export interface ChartRow {
  day: number
  median?: number
  cur?: number // current season, archive data
  fc?: number // 14-day forecast, cumulative; starts at the last archive day so the line connects
  band?: [number, number] // p10 to p90 fan, from the end of the forecast to the last day
  [pastSeason: string]: number | [number, number] | undefined
}

export interface Series {
  rows: ChartRow[]
  lastDay: number
  todayDay: number | null // in-progress season only
  end: { day: number; value: number } // where the end marker sits
  yMax: number
  yTicks: number[]
  monthTicks: { day: number; label: string }[]
}

const MONTHS = ['Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug']
const MONTH_NUMBERS = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]

// Round the axis maximum up so four equal steps land on tidy numbers (five gridlines including zero).
function niceAxis(max: number): { yMax: number; yTicks: number[] } {
  const rough = (max || 1) / 4
  const pow = 10 ** Math.floor(Math.log10(rough))
  const step = ([1, 2, 2.5, 5, 10].find((n) => n * pow >= rough) ?? 10) * pow
  return { yMax: step * 4, yTicks: [0, 1, 2, 3, 4].map((i) => step * i) }
}

export function buildSeries(data: PointResponse, metric: Metric): Series {
  const { season, daily, forecast, history, climatology } = data
  const startYear = Number(season.label.slice(0, 4))
  const lastDay = dayOfSeason(season.label, season.end)
  const rows: ChartRow[] = Array.from({ length: lastDay + 1 }, (_, day) => ({ day }))

  // Past seasons and their per-day median.
  history.forEach((h, i) => {
    for (const c of h.cumulative) if (c.day <= lastDay) rows[c.day][`h${i}`] = c[metric]
  })
  for (const row of rows) {
    const m = median(history.map((_, i) => row[`h${i}`]).filter((v): v is number => typeof v === 'number'))
    if (m != null) row.median = m
  }

  // Current season, and the forecast joined onto its last point. `daily` holds the days up to today; the last few of
  // them can be tagged source "forecast" (the archive lags about 5 days), but they are past days, so they stay on the
  // solid line. Only `forecast.daily` is drawn dotted.
  let last: { day: number; value: number } | null = null
  const forecastRows = forecast?.daily ?? []
  for (const r of daily) {
    const day = dayOfSeason(season.label, r.date)
    if (rows[day]) {
      rows[day].cur = r[metric]
      last = { day, value: r[metric] }
    }
  }
  let fcEnd: { day: number; value: number } | null = null
  if (last) rows[last.day].fc = last.value
  for (const r of forecastRows) {
    const day = dayOfSeason(season.label, r.date)
    if (!rows[day]) continue
    rows[day].fc = r[metric]
    if (!fcEnd || day > fcEnd.day) fcEnd = { day, value: r[metric] }
  }

  // End-of-season fan: from the end of the forecast out to p10 / p90 on the last day, shaped like the median curve.
  const inProgress = !season.complete
  const clim = climatology?.[metric]
  const from = fcEnd ?? last
  let end = last ?? { day: lastDay, value: data.totals[metric] }
  if (inProgress && clim && from) {
    const m0 = rows[from.day].median ?? 0
    const span = (rows[lastDay].median ?? m0) - m0
    for (let d = from.day; d <= lastDay; d++) {
      const frac = span > 0 ? Math.min(1, Math.max(0, ((rows[d].median ?? m0) - m0) / span)) : (d - from.day) / (lastDay - from.day || 1)
      const at = (target: number) => from.value + (target - from.value) * frac
      const [lo, hi] = [at(clim.p10), at(clim.p90)]
      rows[d].band = [Math.min(lo, hi), Math.max(lo, hi)]
    }
    end = { day: lastDay, value: clim.p50 }
  }

  let max = 0
  for (const row of rows) {
    for (const [k, v] of Object.entries(row)) {
      if (k === 'day') continue
      max = Math.max(max, ...(Array.isArray(v) ? v : typeof v === 'number' ? [v] : []))
    }
  }

  return {
    rows,
    lastDay,
    todayDay: inProgress ? dayOfSeason(season.label, season.as_of) : null,
    end,
    ...niceAxis(max * 1.04),
    monthTicks: MONTHS.map((label, i) => {
      const year = MONTH_NUMBERS[i] >= 9 ? startYear : startYear + 1
      return { day: dayOfSeason(season.label, `${year}-${String(MONTH_NUMBERS[i]).padStart(2, '0')}-01`), label }
    }),
  }
}
