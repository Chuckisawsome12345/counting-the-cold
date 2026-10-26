import { useEffect, useRef, useState } from 'react'
import type { PointResponse } from '../api/types'
import { bloomOutlook, CROP_NEEDS, headline, nextSteps, statusLabel, type CropId } from '../bloomAdvice'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { CheckIcon, WarnIcon } from './icons'

const STORAGE_KEY = 'ctc-crop'
// Below this width the map sits above the results (index.css), so a new pin's answer is off screen.
const STACKED_QUERY = '(max-width: 900px)'

function savedCrop(fallback: string): CropId {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (CROP_NEEDS.some((c) => c.id === saved)) return saved as CropId
  } catch {
    // Storage blocked (private window): fall through to the settings' crop.
  }
  return CROP_NEEDS.some((c) => c.id === fallback) ? (fallback as CropId) : 'almond'
}

interface Props {
  data: PointResponse
  settingsCrop: string // the GDD preset, used as the first guess for the crop
  live: string | null // label of the season still being counted, or null when that season is shown
  revealKey: number // bumps when the user picks a new pin; on phones the card scrolls into view
}

// "Will my trees bloom on time?": the orchard's chill against the crop's need, a verdict, and what to do next.
export default function BloomOutlook({ data, settingsCrop, live, revealKey }: Props) {
  const [cropId, setCropId] = useState<CropId>(() => savedCrop(settingsCrop))
  const crop = CROP_NEEDS.find((c) => c.id === cropId) ?? CROP_NEEDS[0]
  const o = bloomOutlook(data, crop)
  const steps = nextSteps(o, data.season.label, live)
  const stacked = useMediaQuery(STACKED_QUERY)
  const ref = useRef<HTMLElement>(null)

  useEffect(() => {
    if (revealKey > 0 && stacked) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    // Only a new pin should scroll, not a resize.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealKey])

  const choose = (id: CropId) => {
    setCropId(id)
    try {
      localStorage.setItem(STORAGE_KEY, id)
    } catch {
      // Not saved; the choice still applies for this visit.
    }
  }

  // The bar: 0 to a little past whichever is larger, the need or the orchard's chill.
  const top = Math.max(crop.high * 1.4, o.range ? o.range[1] : o.value) * 1.05
  const pct = (v: number) => `${Math.min(100, Math.max(0, (v / top) * 100))}%`
  const round = (v: number) => Math.round(v)
  const customStart = !data.season.portions_start.endsWith('-09-01')

  return (
    <section ref={ref} className={`card bloom-card ${o.status}`} aria-labelledby="bloom-title">
      <div className="bloom-head">
        <div>
          <span className="lbl" id="bloom-title">
            Will my trees bloom on time?
          </span>
          <p className="bloom-sub">
            {o.mode === 'past' ? `The ${data.season.label} winter` : `This winter (${data.season.label})`} · chill portions
          </p>
        </div>
        <div className="seg bloom-crops" role="group" aria-label="Your crop">
          {CROP_NEEDS.map((c) => (
            <button key={c.id} type="button" aria-pressed={c.id === crop.id} onClick={() => choose(c.id)}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="bloom-verdict" role="status">
        <span className="bloom-badge">
          {o.status === 'enough' ? <CheckIcon size={16} /> : <WarnIcon size={16} />}
          {statusLabel(o)}
        </span>
        <strong>{headline(o)}</strong>
      </div>

      <div className="bloom-bar" aria-hidden="true">
        <div className="bloom-need" style={{ left: pct(crop.low), width: `calc(${pct(crop.high)} - ${pct(crop.low)})` }} />
        {o.range && <div className="bloom-range" style={{ left: pct(o.range[0]), width: `calc(${pct(o.range[1])} - ${pct(o.range[0])})` }} />}
        <div className="bloom-mark" style={{ left: pct(o.value) }} />
      </div>
      <p className="bloom-numbers">
        <span>
          <i className="key need" /> {crop.label} ({crop.variety}) needs about <b>{crop.low} to {crop.high}</b>
        </span>
        <span>
          <i className="key mark" />{' '}
          {o.mode === 'past' ? (
            <>
              This orchard got <b>{o.value.toFixed(1)}</b>
            </>
          ) : (
            <>
              Likely by spring: <b>about {round(o.value)}</b> (range {round(o.range![0])} to {round(o.range![1])}); {o.soFar > 0 ? `${o.soFar.toFixed(1)} so far` : 'none so far'}
            </>
          )}
          {o.error != null && <> · our estimates are typically within ±{o.error.toFixed(0)}</>}
        </span>
      </p>
      <p className="bloom-note">
        {crop.note}
        {o.early && ' Chill is just starting, so this outlook comes from how the last 10 winters here ended.'}
        {customStart && ' These needs assume chill counted from Sep 1; your start date differs.'}
      </p>

      <h3 className="bloom-steps-title">What to do</h3>
      <ol className="bloom-steps">
        {steps.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      <p className="bloom-fine">
        Options UC farm advisors discuss for low-chill years, not prescriptions. Follow product labels, and check with your{' '}
        <a href="https://ucanr.edu/About/Locations/" target="_blank" rel="noreferrer">
          UC Cooperative Extension farm advisor
        </a>{' '}
        or{' '}
        <a href="https://ipm.ucanr.edu" target="_blank" rel="noreferrer">
          UC IPM
        </a>{' '}
        before acting.
      </p>
    </section>
  )
}
