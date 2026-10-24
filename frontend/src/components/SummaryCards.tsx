import type { PointResponse } from '../api/types'
import { dayOfSeason, formatFixed, formatMonthDay, formatNumber, median } from '../format'
import { useCountUp } from '../hooks/useCountUp'
import { useSingleOpen } from '../hooks/useSingleOpen'
import { METRICS, isUnavailable, type MetricInfo } from '../metrics'
import InfoButton from './InfoButton'
import { metricCopy } from './metricInfo'

const STAGGER_MS = 80

interface CardProps {
  data: PointResponse
  info: MetricInfo
  index: number
  open: boolean
  onToggle: () => void
  onClose: () => void
}

function MetricCard({ data, info, index, open, onToggle, onClose }: CardProps) {
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

  const unavailable = isUnavailable(data, metric)
  const noneYet = inProgress && (value === 0 || !med)
  const pct = med ? ((value - med) / med) * 100 : null
  const arrow = pct === null || Math.abs(pct) < 0.05 ? '◦' : pct > 0 ? '▲' : '▼'

  const biggest = Math.max(value, ...history.map((h) => h.totals[metric]))
  const barWidth = biggest > 0 ? Math.min(100, (shown / (biggest * 1.1)) * 100) : 0

  const start = season[startField]
  // Gain over the next 14 days. forecast.daily is cumulative season-to-date (api-contract.md) and the backend's
  // plus14 is the cumulative value on day 14, so the gain is that minus what has accumulated so far.
  const day14 = forecast?.daily[Math.min(13, (forecast?.daily.length ?? 1) - 1)]
  const plus14 = forecast ? Math.max(0, (day14?.[metric] ?? forecast.plus14[metric]) - value) : 0
  const err = correction.expected_error?.[metric]

  // One line for the "i" panel, from the same values the card shows. Left out when the card has no number.
  let live: string | undefined
  if (!unavailable) {
    const mine = `${formatFixed(value, digits)} ${footUnit}`
    const forDate = inProgress ? ' for this date' : ''
    if (noneYet) live = `Your pin: nothing counted yet, ${startText(formatMonthDay(start))}.`
    else if (pct === null) live = `Your pin: ${mine}.`
    else if (Math.abs(pct) < 0.05) live = `Your pin: ${mine}, in line with the 10-season median${forDate}.`
    else live = `Your pin: ${mine}, ${Math.abs(pct).toFixed(1)}% ${pct > 0 ? 'above' : 'below'} the 10-season median${forDate}.`
  }

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
        <div className="metric-title">
          <span className="lbl">{label}</span>
          <InfoButton
            title={label}
            copy={metricCopy(metric, { gddBaseF: settings.gdd_base_f, gddUpperF: settings.gdd_upper_f })}
            live={live}
            accent={accent}
            open={open}
            onToggle={onToggle}
            onClose={onClose}
          />
        </div>
        <span className="metric-unit">{unit}</span>
      </div>
      <div className="metric-value">{unavailable ? '—' : value === 0 ? '0' : formatFixed(shown, digits)}</div>
      <div className="metric-delta">
        {unavailable ? (
          <strong>◦ Not available yet</strong>
        ) : noneYet ? (
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
  const { openId, toggle, close } = useSingleOpen()
  return (
    <div className="cards" role="group" aria-label="Season summary">
      <h2 className="sr-only">Season summary</h2>
      {METRICS.map((info, i) => (
        <MetricCard
          key={info.metric}
          data={data}
          info={info}
          index={i}
          open={openId === info.metric}
          onToggle={() => toggle(info.metric)}
          onClose={close}
        />
      ))}
    </div>
  )
}
