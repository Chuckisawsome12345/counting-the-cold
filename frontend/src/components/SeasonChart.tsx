import { useMemo, useState, type KeyboardEvent } from 'react'
import { Area, CartesianGrid, ComposedChart, Line, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis, usePlotArea } from 'recharts'
import type { Metric, PointResponse } from '../api/types'
import { buildSeries, type Series } from '../chartData'
import { formatFixed, formatMonthDay, formatNumber } from '../format'
import { NARROW_QUERY, useMediaQuery } from '../hooks/useMediaQuery'
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion'
import { METRICS, type MetricInfo } from '../metrics'
import ForecastChart from './ForecastChart'

const DRAW_MS = 1400
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

// Gradients stretched across the whole plot width: cold at the start of the season, heat at the end.
function Gradients() {
  const area = usePlotArea()
  if (!area) return null
  const span = { gradientUnits: 'userSpaceOnUse' as const, x1: area.x, x2: area.x + area.width, y1: 0, y2: 0 }
  return (
    <defs>
      <linearGradient id="ctc-stroke" {...span}>
        <stop offset="0" style={{ stopColor: 'var(--cold4)' }} />
        <stop offset="0.38" style={{ stopColor: 'var(--cold3)' }} />
        <stop offset="0.72" style={{ stopColor: 'var(--heat1)' }} />
        <stop offset="1" style={{ stopColor: 'var(--heat3)' }} />
      </linearGradient>
      <linearGradient id="ctc-area" {...span}>
        <stop offset="0" style={{ stopColor: 'var(--cold3)', stopOpacity: 0.28 }} />
        <stop offset="0.5" style={{ stopColor: 'var(--cold3)', stopOpacity: 0.08 }} />
        <stop offset="1" style={{ stopColor: 'var(--heat3)', stopOpacity: 0.14 }} />
      </linearGradient>
    </defs>
  )
}

function dayToDate(startYear: number, day: number) {
  const d = new Date(Date.UTC(startYear, 8, 1 + day))
  return `${MONTH_NAMES[d.getUTCMonth()]} ${d.getUTCDate()}`
}

function ChartTooltip({ active, label, series, info, startYear }: { active?: boolean; label?: number; series: Series; info: MetricInfo; startYear: number }) {
  const row = active && label != null ? series.rows[label] : undefined
  if (!row) return null
  const fmt = (v: number | undefined) => (v == null ? null : `${formatFixed(v, info.digits)} ${info.footUnit}`)
  const pastValues = Object.entries(row)
    .filter(([k, v]) => /^h\d+$/.test(k) && typeof v === 'number')
    .map(([, v]) => v as number)
  const lines: [string, string | null][] = [
    [row.cur != null ? 'This season' : 'Forecast', fmt(row.cur ?? row.fc)],
    ['10-season median', fmt(row.median)],
    ['Past seasons', pastValues.length ? `${formatFixed(Math.min(...pastValues), info.digits)} to ${formatFixed(Math.max(...pastValues), info.digits)}` : null],
  ]
  return (
    <div className="chart-tip">
      <strong>{dayToDate(startYear, row.day)}</strong>
      {lines.map(([name, value]) => value && (
        <span key={name}>
          {name}: <b>{value}</b>
        </span>
      ))}
    </div>
  )
}

function summarize(data: PointResponse, info: MetricInfo, series: Series): string {
  const value = formatFixed(data.totals[info.metric], info.digits)
  const med = series.rows[series.lastDay].median
  if (data.season.complete) {
    const rel =
      med == null ? '' : Math.abs(data.totals[info.metric] - med) / med < 0.03 ? ', near' : data.totals[info.metric] > med ? ', above' : ', below'
    return `${info.label} for ${data.season.label} end at ${value}${rel}${med == null ? '' : ` the ten-season median of ${formatFixed(med, info.digits)}`}.`
  }
  const clim = data.climatology?.[info.metric]
  return `${info.label} for ${data.season.label} so far: ${value}.${clim ? ` Projected season end: median ${formatFixed(clim.p50, info.digits)}, range ${formatFixed(clim.p10, info.digits)} to ${formatFixed(clim.p90, info.digits)}.` : ''}`
}

interface Props {
  data: PointResponse
  metric: Metric
  onMetric: (metric: Metric) => void
}

export default function SeasonChart({ data, metric, onMetric }: Props) {
  const reduced = usePrefersReducedMotion()
  const narrow = useMediaQuery(NARROW_QUERY)
  const info = METRICS.find((m) => m.metric === metric) ?? METRICS[0]
  const series = useMemo(() => buildSeries(data, metric), [data, metric])
  const { season } = data
  const startYear = Number(season.label.slice(0, 4))

  // The current line draws in once per season and pin; switching metric only cross-fades.
  const animKey = `${season.label}|${data.location.lat},${data.location.lon}`
  const [drawnFor, setDrawnFor] = useState('')
  const draw = !reduced && drawnFor !== animKey

  const onTabKeys = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = METRICS.findIndex((m) => m.metric === metric)
    const next = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : null
    if (next === null) return
    e.preventDefault()
    const target = METRICS[(next + METRICS.length) % METRICS.length]
    onMetric(target.metric)
    document.getElementById(`tab-${target.metric}`)?.focus()
  }

  return (
    <section className={`card chart-card ${info.accent}`}>
      <div className="chart-head">
        <div>
          <span className="lbl">Season chart · cumulative by day</span>
          <h2 className="chart-title">{info.label}</h2>
        </div>
        <div className="metric-tabs" role="tablist" aria-label="Metric" onKeyDown={onTabKeys}>
          {METRICS.map((m) => (
            <button
              key={m.metric}
              id={`tab-${m.metric}`}
              type="button"
              role="tab"
              aria-selected={m.metric === metric}
              aria-controls="chart-panel"
              tabIndex={m.metric === metric ? 0 : -1}
              onClick={() => onMetric(m.metric)}
            >
              <span className="t-long">{m.label === 'Growing Degree Days' ? 'GDD' : m.label}</span>
              <span className="t-short">{m.short}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="chart-legend">
        <span>
          <i className="sw past" aria-hidden="true" />
          10 past seasons
        </span>
        <span>
          <i className="sw median" aria-hidden="true" />
          10-season median
        </span>
        <span>
          <i className="sw current" aria-hidden="true" />
          {season.label} ({season.complete ? 'complete' : `in progress, ${formatMonthDay(season.as_of)}`})
        </span>
        {!season.complete && (
          <span>
            <i className="sw fan" aria-hidden="true" />
            Forecast p10 to p90
          </span>
        )}
      </div>

      <div id="chart-panel" role="tabpanel" aria-labelledby={`tab-${metric}`}>
        <div className="chart-fade" key={metric} role="img" aria-label={summarize(data, info, series)}>
          <ResponsiveContainer width="100%" height={narrow ? 240 : 300}>
            <ComposedChart accessibilityLayer={false} data={series.rows} margin={{ top: 26, right: narrow ? 16 : 30, bottom: 4, left: 0 }}>
              <Gradients />
              <CartesianGrid vertical={false} stroke="var(--line)" />
              <XAxis
                dataKey="day"
                type="number"
                domain={[0, series.lastDay]}
                ticks={series.monthTicks.filter((_, i) => !narrow || i % 2 === 0).map((t) => t.day)}
                tickFormatter={(d: number) => series.monthTicks.find((t) => t.day === d)?.label ?? ''}
                tickLine={false}
                axisLine={{ stroke: 'var(--line)' }}
                tick={{ fontSize: 11, fill: 'var(--ink3)' }}
              />
              <YAxis
                domain={[0, series.yMax]}
                ticks={series.yTicks}
                tickLine={false}
                axisLine={false}
                width={narrow ? 38 : 46}
                tick={{ fontSize: 11, fill: 'var(--ink3)' }}
                tickFormatter={(n: number) => formatNumber(n, 1)}
              />
              <Tooltip
                isAnimationActive={false}
                cursor={{ stroke: 'var(--line2)' }}
                content={<ChartTooltip series={series} info={info} startYear={startYear} />}
              />

              {data.history.map((h, i) => (
                <Line
                  key={h.season}
                  dataKey={`h${i}`}
                  stroke="var(--ink3)"
                  strokeOpacity={0.38}
                  strokeWidth={1.2}
                  dot={false}
                  activeDot={false}
                  className="past-line"
                  isAnimationActive={false}
                />
              ))}
              <Line dataKey="median" stroke="var(--ink2)" strokeWidth={1.8} strokeDasharray="6 5" dot={false} activeDot={false} isAnimationActive={false} />

              {season.complete && <Area dataKey="cur" stroke="none" fill="url(#ctc-area)" isAnimationActive={false} activeDot={false} />}
              <ForecastChart series={series} asOf={season.as_of} />

              <Line
                dataKey="cur"
                stroke="url(#ctc-stroke)"
                strokeOpacity={0.25}
                strokeWidth={7}
                dot={false}
                activeDot={false}
                className="glow-line"
                isAnimationActive={draw}
                animationDuration={DRAW_MS}
              />
              <Line
                dataKey="cur"
                stroke="url(#ctc-stroke)"
                strokeWidth={3.2}
                dot={false}
                activeDot={{ r: 4 }}
                isAnimationActive={draw}
                animationDuration={DRAW_MS}
                onAnimationEnd={() => setDrawnFor(animKey)}
              />

              <ReferenceDot
                x={series.end.day}
                y={series.end.value}
                r={6}
                ifOverflow="visible"
                fill="var(--bg)"
                stroke="var(--heat1)"
                strokeWidth={3}
                label={{
                  content: ({ viewBox }) => {
                    const box = viewBox as { x: number; y: number; width: number }
                    const clim = data.climatology?.[metric]
                    const text = season.complete
                      ? `${formatFixed(data.totals[metric], info.digits)} · season complete`
                      : clim
                        ? `p50 ${formatFixed(clim.p50, info.digits)} · p10 ${formatFixed(clim.p10, info.digits)} to p90 ${formatFixed(clim.p90, info.digits)}`
                        : ''
                    return (
                      <text x={box.x + box.width} y={box.y - 10} textAnchor="end" fontSize={13} fontWeight={700} fill="var(--ink)">
                        {text}
                      </text>
                    )
                  },
                }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  )
}
