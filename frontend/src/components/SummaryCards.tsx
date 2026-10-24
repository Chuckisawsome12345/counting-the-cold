import type { PointResponse } from '../api/types'
import { dayOfSeason, formatFixed, formatMonthDay, formatNumber, median } from '../format'
import { useCountUp } from '../hooks/useCountUp'
import { METRICS, type MetricInfo } from '../metrics'

const STAGGER_MS = 80

function MetricCard({ data, info, index }: { data: PointResponse; info: MetricInfo; index: number }) {
  const { metric, label, unit, footUnit, digits, accent, startField, startText } = info
  const { season, forecast, correction, history, settings } = data
  const value = data.totals[metric]
  const inProgress = !season.complete

  // Median of the previous 10 seasons: end-of-season totals for a finished season, the same day of season otherwise.
  const day = inProgress ? dayOfSeason(season.label, season.as_of) : null
  const pastValues = history
    .map((h) => (day === null ? h.totals[metric] : h.cumulative.find((c) => c.day === day)?.[metric]))
    .filter((v): v is number => v != null)
  const med = median(pastValues)

  const runKey = `${season.label}|${settings.crop}|${settings.corrected}|${data.location.lat},${data.location.lon}`
  const shown = useCountUp(value, runKey, index * STAGGER_MS)

  const noneYet = inProgress && (value === 0 || !med)
  const pct = med ? ((value - med) / med) * 100 : null
  const arrow = pct === null || Math.abs(pct) < 0.05 ? '◦' : pct > 0 ? '▲' : '▼'

  const biggest = Math.max(value, ...history.map((h) => h.totals[metric]))
  const barWidth = biggest > 0 ? Math.min(100, (shown / (biggest * 1.1)) * 100) : 0

  const start = season[startField]
  const plus14 = forecast?.plus14[metric] ?? 0
  const err = correction.expected_error?.[metric]

  let footLeft: string
  if (!inProgress) {
    footLeft =
      metric === 'gdd'
        ? `Base ${settings.gdd_base_f}°F · ${settings.gdd_upper_f == null ? 'no upper cutoff' : `upper ${settings.gdd_upper_f}°F`}`
        : 'Season complete'
  } else if (plus14 > 0) {
    footLeft = `+14 d: +${formatNumber(plus14, digits)} ${footUnit}`
  } else if (start > season.as_of) {
    footLeft = `Starts ${formatMonthDay(start)}`
  } else {
    footLeft = `+14 d: +0 ${footUnit}`
  }

  return (
    <div className={`card metric ${accent}`}>
      <div className="metric-head">
        <span className="lbl">{label}</span>
        <span className="metric-unit">{unit}</span>
      </div>
      <div className="metric-value">{value === 0 ? '0' : formatFixed(shown, digits)}</div>
      <div className="metric-delta">
        {noneYet ? (
          <>
            <strong>◦ None yet</strong>
            <span>{startText(formatMonthDay(start))}</span>
          </>
        ) : pct === null ? (
          <strong>◦ No 10-season median</strong>
        ) : (
          <>
            <strong>
              {arrow} {Math.abs(pct).toFixed(1)}%
            </strong>
            <span>
              vs <span className="t-long">10-season </span>median
            </span>
          </>
        )}
      </div>
      <div className="metric-bar" aria-hidden="true">
        <i style={{ width: `${barWidth}%` }} />
      </div>
      <div className="metric-foot">
        <span>{footLeft}</span>
        {err != null && (
          <span>
            ± {formatNumber(err, 1)} {footUnit} expected
          </span>
        )}
      </div>
    </div>
  )
}

export default function SummaryCards({ data }: { data: PointResponse }) {
  return (
    <div className="cards" role="group" aria-label="Season summary">
      <h2 className="sr-only">Season summary</h2>
      {METRICS.map((info, i) => (
        <MetricCard key={info.metric} data={data} info={info} index={i} />
      ))}
    </div>
  )
}
