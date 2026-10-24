import type { Metric, PointResponse } from '../api/types'

const CARDS: { metric: Metric; label: string; unit: string }[] = [
  { metric: 'chill_portions', label: 'Chill portions', unit: 'CP' },
  { metric: 'chill_hours', label: 'Chill hours', unit: 'h' },
  { metric: 'utah_units', label: 'Utah units', unit: 'CU' },
  { metric: 'gdd', label: 'Growing degree days', unit: '°F-days' },
]

function median(values: number[]) {
  const s = [...values].sort((a, b) => a - b)
  const mid = Math.floor(s.length / 2)
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2
}

// TODO(C): compare against the median at the same day of season (not season totals) for the current season.
export default function SummaryCards({ data }: { data: PointResponse }) {
  return (
    <div className="cards">
      {CARDS.map(({ metric, label, unit }) => {
        const value = data.totals[metric]
        const med = median(data.history.map((h) => h.totals[metric]))
        const pct = med ? Math.round(((value - med) / med) * 100) : 0
        const err = data.correction.expected_error?.[metric]
        return (
          <div className="card" key={metric}>
            <div className="card-label">{label}</div>
            <div className="card-value">
              {Math.round(value).toLocaleString()} <span className="card-unit">{unit}</span>
            </div>
            {err != null && <div className="card-sub">± {Math.round(err)} expected error</div>}
            {data.season.complete && (
              <div className={pct >= 0 ? 'card-sub up' : 'card-sub down'}>
                {pct >= 0 ? '▲' : '▼'} {Math.abs(pct)}% vs 10-season median
              </div>
            )}
            {data.forecast && (
              <div className="card-sub">+14 days: {Math.round(data.forecast.plus14[metric]).toLocaleString()}</div>
            )}
          </div>
        )
      })}
    </div>
  )
}
