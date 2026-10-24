import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import type { Metric, PointResponse } from '../api/types'
import { formatFixed } from '../format'
import { NARROW_QUERY, useMediaQuery } from '../hooks/useMediaQuery'
import { METRICS, isUnavailable } from '../metrics'

interface BarItem {
  season: string // "2025-26"
  short: string // "25-26"
  value: number
  current: boolean
}

// "2015-16" -> "15-16"
const shortSeason = (label: string) => `${label.slice(2, 4)}-${label.slice(5)}`

// The 10 previous seasons plus this one. A finished season uses its total; an in-progress season shows the
// projected median (p50) as a hatched bar, because its total is not known yet.
function buildBars(data: PointResponse, metric: Metric): BarItem[] {
  const bars: BarItem[] = data.history.map((h) => ({ season: h.season, short: shortSeason(h.season), value: h.totals[metric], current: false }))
  const value = data.season.complete ? data.totals[metric] : data.climatology?.[metric].p50
  if (value != null) bars.push({ season: data.season.label, short: shortSeason(data.season.label), value, current: true })
  return bars
}

export default function SeasonTotals({ data, metric }: { data: PointResponse; metric: Metric }) {
  const narrow = useMediaQuery(NARROW_QUERY)
  const info = METRICS.find((m) => m.metric === metric) ?? METRICS[0]
  const bars = buildBars(data, metric)
  const complete = data.season.complete
  const current = bars.find((b) => b.current)
  const past = bars.filter((b) => !b.current).map((b) => b.value)
  const summary =
    `${info.label} season totals for the ${past.length} seasons before this one range from ${formatFixed(Math.min(...past), info.digits)} to ${formatFixed(Math.max(...past), info.digits)}.` +
    (current ? ` ${data.season.label}: ${complete ? '' : 'projected about '}${formatFixed(current.value, info.digits)}.` : '')

  return (
    <section className={`card totals-card ${info.accent}`}>
      <h2 className="sr-only">Season totals</h2>
      <span className="lbl">Season totals · this season and the 10 before</span>
      {isUnavailable(data, metric) ? (
        <div className="unavailable" role="status">
          <strong>{info.label} isn't available yet.</strong>
          <span>Nothing to compare until the data service calculates it.</span>
        </div>
      ) : (
      <div role="img" aria-label={summary} className="chart-fade" key={metric}>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart accessibilityLayer={false} data={bars} margin={{ top: 22, right: 4, bottom: 0, left: 4 }}>
            <defs>
              <linearGradient id="ctc-bar-past" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" style={{ stopColor: 'var(--cold2)' }} />
                <stop offset="1" style={{ stopColor: 'var(--cold1)' }} />
              </linearGradient>
              <linearGradient id="ctc-bar-now" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" style={{ stopColor: 'var(--heat1)' }} />
                <stop offset="1" style={{ stopColor: 'var(--acc2)' }} />
              </linearGradient>
              <pattern id="ctc-bar-hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="8" height="8" style={{ fill: 'var(--solid)' }} />
                <rect width="4" height="8" style={{ fill: 'var(--acc2)' }} />
              </pattern>
            </defs>
            <XAxis dataKey="short" tickLine={false} axisLine={false} interval={narrow ? 1 : 0} tick={{ fontSize: narrow ? 9 : 10, fill: 'var(--ink3)' }} />
            <YAxis hide domain={[0, (max: number) => max * 1.08]} />
            <Bar dataKey="value" radius={[5, 5, 0, 0]} isAnimationActive={false}>
              {bars.map((b) => (
                <Cell key={b.season} fill={b.current ? (complete ? 'url(#ctc-bar-now)' : 'url(#ctc-bar-hatch)') : 'url(#ctc-bar-past)'} />
              ))}
              <LabelList
                dataKey="value"
                content={({ x, y, width, value, index }) => {
                  const isNow = bars[index as number]?.current
                  return (
                    <text
                      x={(x as number) + (width as number) / 2}
                      y={(y as number) - 6}
                      textAnchor="middle"
                      fontSize={10}
                      fontWeight={isNow ? 700 : 400}
                      fill={isNow ? 'var(--ink)' : 'var(--ink3)'}
                    >
                      {!complete && isNow ? '~' : ''}
                      {formatFixed(value as number, info.digits)}
                    </text>
                  )
                }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      )}
    </section>
  )
}
