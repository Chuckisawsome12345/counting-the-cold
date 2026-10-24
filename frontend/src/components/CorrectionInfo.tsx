import type { Correction } from '../api/types'

// Segment colours for the weight bar, in station order.
const SEGMENT_COLOURS = ['var(--cold3)', 'var(--cold4)', 'var(--heat1)', 'var(--heat2)', 'var(--cold2)']

const percent = (weight: number) => {
  const p = Math.round(weight * 100)
  return p === 0 && weight > 0 ? '<1%' : `${p}%`
}

export default function CorrectionInfo({ correction }: { correction: Correction }) {
  const { applied, stations } = correction
  return (
    <section className="card correction-card">
      <span className="lbl">Correction</span>
      {!applied ? (
        <p>Raw estimate shown. Turn on bias correction to calibrate with nearby stations.</p>
      ) : stations.length === 0 ? (
        <p>Bias correction applied.</p>
      ) : (
        <>
          <p>
            Corrected using{' '}
            {stations.map((s, i) => (
              <span key={s.id}>
                {i > 0 && ' · '}
                {i === 0 ? <strong>{s.active ? s.name : `${s.name} (historical)`}</strong> : s.active ? s.name : `${s.name} (historical)`}{' '}
                {percent(s.weight)}
              </span>
            ))}
          </p>
          <div className="weight-bar" aria-hidden="true">
            {stations.map((s, i) => (
              <i key={s.id} style={{ flex: Math.max(s.weight, 0.005), background: SEGMENT_COLOURS[i % SEGMENT_COLOURS.length] }} />
            ))}
          </div>
        </>
      )}
    </section>
  )
}
