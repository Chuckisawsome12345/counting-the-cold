import { useEffect, useState } from 'react'
import { fetchValidation } from '../api/client'
import type { Metric, Station, StationValidation, ValidationResponse } from '../api/types'
import { formatDate } from '../geo'
import { formatFixed } from '../format'
import { useCountDown } from '../hooks/useCountDown'
import { METRICS, type MetricInfo } from '../metrics'

type Load = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: ValidationResponse }

// "Improvement" is how much smaller the corrected error is than the raw error, as a percent of the raw error.
const improvement = (raw: number, corrected: number) => (raw > 0 ? ((raw - corrected) / raw) * 100 : 0)

function Headline({ info, raw, corrected, count }: { info: MetricInfo; raw: number; corrected: number; count: number }) {
  const gain = Math.round(improvement(raw, corrected))
  const shown = useCountDown(raw, corrected, info.metric)
  return (
    <section className="card v-headline">
      <div className="v-headline-text">
        <span className="lbl">Average error across {count} validation stations</span>
        <p>
          {gain > 0
            ? `Tested on seasons we already know. Our correction cuts the average miss by ${gain}%.`
            : 'Tested on seasons we already know. For this measure the correction did not reduce the average miss.'}
        </p>
      </div>
      <div className="v-numbers">
        <div className="v-num raw">
          <span className="lbl">Raw</span>
          <span className="v-big">±{formatFixed(raw, info.digits)}</span>
          <span className="v-unit">{info.unit}</span>
        </div>
        <svg className="v-arrow" width="60" height="24" viewBox="0 0 60 24" aria-hidden="true">
          <path d="M2 12h54M46 4l10 8-10 8" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <div className="v-num corrected">
          <span className="lbl">Corrected</span>
          <span className="v-big">±{formatFixed(shown, info.digits)}</span>
          <span className="v-unit">
            {info.unit}
            {gain > 0 && <> · {gain}% smaller</>}
          </span>
        </div>
      </div>
    </section>
  )
}

function StationRow({ s, info, closed }: { s: StationValidation; info: MetricInfo; closed: boolean }) {
  const e = s.mae[info.metric]
  if (!e) return null
  const pct = improvement(e.raw_mae, e.corrected_mae)
  return (
    <tr className={closed ? 'closed-row' : undefined}>
      <th scope="row">
        {s.name} #{s.id}
        {closed && <span className="closed-tag">CLOSED</span>}
      </th>
      <td>{s.seasons.length}</td>
      <td className="raw">±{formatFixed(e.raw_mae, info.digits)}</td>
      <td className="corr">±{formatFixed(e.corrected_mae, info.digits)}</td>
      <td>
        <span className="impr">
          <span className="impr-bar" aria-hidden="true">
            <i style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} />
          </span>
          <span className="impr-pct">
            {pct >= 0 ? '▼' : '▲'} {Math.abs(Math.round(pct))}%
          </span>
        </span>
      </td>
    </tr>
  )
}

export default function ValidationPanel({ stations }: { stations: Station[] }) {
  const [load, setLoad] = useState<Load>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  const [metric, setMetric] = useState<Metric>('chill_portions')
  const info = METRICS.find((m) => m.metric === metric) ?? METRICS[0]

  useEffect(() => {
    let cancelled = false
    fetchValidation()
      .then((data) => !cancelled && setLoad({ status: 'ready', data }))
      .catch((e: Error) => !cancelled && setLoad({ status: 'error', message: e.message }))
    return () => {
      cancelled = true
    }
  }, [attempt])

  if (load.status === 'loading') {
    return (
      <div className="v-page" role="status" aria-label="Loading accuracy results">
        <div className="skeleton" style={{ height: 150, borderRadius: 18 }} />
        <div className="skeleton" style={{ height: 360, borderRadius: 18 }} />
      </div>
    )
  }

  if (load.status === 'error') {
    return (
      <div className="v-page">
        <div className="banner error" role="alert">
          <span>Couldn't load the accuracy results ({load.message}).</span>
          <button
            type="button"
            className="chip"
            onClick={() => {
              setLoad({ status: 'loading' })
              setAttempt((n) => n + 1)
            }}
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  const { data } = load
  if (!data.built_at || data.stations.length === 0) {
    return (
      <div className="v-page">
        <section className="card v-empty">
          <span className="lbl">Accuracy</span>
          <h2>The accuracy check hasn't been built yet</h2>
          <p>
            We compare our estimates with real CIMIS stations to show how far off they are, raw and corrected. Those results aren't ready
            yet, so there are no numbers to show here. Check back soon.
          </p>
        </section>
      </div>
    )
  }

  const summary = data.summary[metric]
  const closedIds = new Set(stations.filter((s) => !s.active).map((s) => s.id))
  const closed = stations.find((s) => !s.active && data.stations.some((v) => v.id === s.id))
  // Closed stations first (Durham is the story), then the order the API gives.
  const rows = [...data.stations]
    .filter((s) => s.mae[metric])
    .sort((a, b) => Number(closedIds.has(b.id)) - Number(closedIds.has(a.id)))

  return (
    <div className="v-page">
      {summary ? (
        <Headline info={info} raw={summary.raw_mae} corrected={summary.corrected_mae} count={data.stations.length} />
      ) : (
        <section className="card v-empty">
          <p>No overall error was calculated for {info.label}.</p>
        </section>
      )}

      <section className="card v-table-card">
        <div className="v-table-head">
          <div>
            <span className="lbl">Per-station results</span>
            <p className="v-sub">
              Average error in {info.footUnit}, raw vs corrected. Built {formatDate(data.built_at.slice(0, 10))}.
            </p>
          </div>
          <div className="seg" role="group" aria-label="Measure">
            {METRICS.map((m) => (
              <button key={m.metric} type="button" aria-pressed={m.metric === metric} onClick={() => setMetric(m.metric)}>
                <span className="t-long">{m.label === 'Growing Degree Days' ? 'GDD' : m.label}</span>
                <span className="t-short">{m.short}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="table-scroll">
          <table className="vtable">
            <thead>
              <tr>
                <th scope="col">Station</th>
                <th scope="col">Seasons</th>
                <th scope="col">Raw</th>
                <th scope="col">Corrected</th>
                <th scope="col">Improvement</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <StationRow key={s.id} s={s} info={info} closed={closedIds.has(s.id)} />
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {closed && (
        <section className="card v-callout">
          <strong>
            {closed.name} #{closed.id} closed{closed.disconnect_date ? ` ${formatDate(closed.disconnect_date)}` : ''}.
          </strong>{' '}
          Its decade of records still calibrates our estimate.
        </section>
      )}
    </div>
  )
}
