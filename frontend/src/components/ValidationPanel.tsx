import { useEffect, useState } from 'react'
import { fetchValidation } from '../api/client'
import type { Metric, Station, StationValidation, ValidationResponse } from '../api/types'
import { formatDate } from '../geo'
import { formatFixed } from '../format'
import { useRawToCorrected } from '../hooks/useRawToCorrected'
import { METRICS, type MetricInfo } from '../metrics'
import AccuracyMap, { type AccuracyRow } from './AccuracyMap'

type Load = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: ValidationResponse }

// "Improvement" is how much smaller the corrected error is than the raw error, as a percent of the raw error.
const improvement = (raw: number, corrected: number) => (raw > 0 ? ((raw - corrected) / raw) * 100 : 0)

// A row's change in words: an arrow and a percent, or "no change" when the correction left the error as it was.
const changeText = (pct: number) => (Math.round(pct) === 0 ? 'no change' : `${pct > 0 ? '▼' : '▲'} ${Math.abs(Math.round(pct))}%`)

// The sentence under the headline, worked out from the numbers for whichever measure is selected.
function headlineText(name: string, raw: number, corrected: number, gain: number) {
  const intro = 'Tested on seasons we already know.'
  if (gain > 0) return `${intro} For ${name}, our correction cuts the average miss by ${gain}%.`
  if (corrected > raw) return `${intro} For ${name}, the correction did not reduce the average miss.`
  return `${intro} For ${name}, the correction made no change to the average miss.`
}

// `progress` runs 0 (raw) to 1 (corrected); the corrected number counts down in step with the map's bubbles.
function Headline({ info, raw, corrected, count, progress }: { info: MetricInfo; raw: number; corrected: number; count: number; progress: number }) {
  const gain = Math.round(improvement(raw, corrected))
  const shown = raw + (corrected - raw) * progress
  return (
    <section className="card v-headline">
      <div className="v-headline-text">
        <span className="lbl">Average error across {count} validation stations</span>
        <p>{headlineText(info.metric === 'gdd' ? 'GDD' : info.label, raw, corrected, gain)}</p>
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
            {gain > 0 ? <> · {gain}% smaller</> : corrected === raw && <> · no change</>}
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
          <span className="impr-pct">{changeText(pct)}</span>
        </span>
      </td>
    </tr>
  )
}

function Results({ data, stations }: { data: ValidationResponse; stations: Station[] }) {
  // Opens on GDD: it is the measure the correction improves, so the raw-to-corrected animation has something to show.
  const [metric, setMetric] = useState<Metric>('gdd')
  const info = METRICS.find((m) => m.metric === metric) ?? METRICS[0]

  const summary = data.summary[metric]
  const closedIds = new Set(stations.filter((s) => !s.active).map((s) => s.id))
  const closed = stations.find((s) => !s.active && data.stations.some((v) => v.id === s.id))
  const closedError = data.stations.find((v) => v.id === closed?.id)?.mae.chill_portions?.corrected_mae
  // Closed stations first (Durham is the story), then the order the API gives.
  const rows = [...data.stations]
    .filter((s) => s.mae[metric])
    .sort((a, b) => Number(closedIds.has(b.id)) - Number(closedIds.has(a.id)))

  // The same rows as map bubbles, for the stations we have a position for.
  const bubbles: AccuracyRow[] = rows.flatMap((v) => {
    const station = stations.find((s) => s.id === v.id)
    const e = v.mae[metric]
    return station && e ? [{ validation: v, station, raw: e.raw_mae, corrected: e.corrected_mae }] : []
  })
  const { progress, overall, mode, play, show } = useRawToCorrected(bubbles.length)

  return (
    <div className="v-page">
      {summary ? (
        <Headline info={info} raw={summary.raw_mae} corrected={summary.corrected_mae} count={data.stations.length} progress={overall} />
      ) : (
        <section className="card v-empty">
          <p>No overall error was calculated for {info.label}.</p>
        </section>
      )}

      <div className="v-grid">
        {bubbles.length > 0 && <AccuracyMap rows={bubbles} info={info} progress={progress} mode={mode} onShow={show} onPlay={play} />}

        <section className="card v-table-card">
          <div className="v-table-head">
            <div>
              <span className="lbl">Per-station results</span>
              <p className="v-sub">
                Average error in {info.footUnit}, raw vs corrected. Built {formatDate(data.built_at?.slice(0, 10) ?? '')}.
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
              <caption className="sr-only">Average error per station, raw and corrected, in {info.footUnit}</caption>
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
          <ul className="v-list">
            {rows.map((s) => {
              const e = s.mae[metric]
              if (!e) return null
              const pct = improvement(e.raw_mae, e.corrected_mae)
              return (
                <li key={s.id} className={closedIds.has(s.id) ? 'closed-row' : undefined}>
                  <span>
                    <strong>
                      {s.name} #{s.id}
                    </strong>
                    {closedIds.has(s.id) && <span className="closed-tag">CLOSED</span>}
                  </span>
                  <span className="v-pair">
                    <span className="raw">±{formatFixed(e.raw_mae, info.digits)}</span> → <span className="corr">±{formatFixed(e.corrected_mae, info.digits)}</span>{' '}
                    <span className="impr-pct">{changeText(pct)}</span>
                  </span>
                </li>
              )
            })}
          </ul>
        </section>
      </div>

      {closed && (
        <section className="card v-callout">
          <strong>
            {closed.name} #{closed.id} closed{closed.disconnect_date ? ` ${formatDate(closed.disconnect_date)}` : ''}.
          </strong>{' '}
          {metric === 'gdd' && 'Its decade of records still calibrates our heat (GDD) estimate.'}
          {/* "Closer than the nearest station" is left out: /api/validation does not carry that comparison yet. */}
          {metric === 'chill_portions' && closedError !== undefined && (
            <>
              Our chill estimate lands within {Math.round(closedError)} chill {Math.round(closedError) === 1 ? 'portion' : 'portions'} at {closed.name}.
            </>
          )}
        </section>
      )}
    </div>
  )
}

export default function ValidationPanel({ stations }: { stations: Station[] }) {
  const [load, setLoad] = useState<Load>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

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

  return <Results data={data} stations={stations} />
}
