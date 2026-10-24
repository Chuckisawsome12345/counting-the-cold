import type { Quality } from '../api/types'
import { CheckIcon, WarnIcon } from './icons'

// UI heuristics for the "check gaps" variant. The API contract defines no thresholds, so these are ours.
const LONG_GAP_HOURS = 12
const MANY_MISSING_HOURS = 72

function Tag({ text, tip }: { text: string; tip: string }) {
  // Focusable so keyboard users can read the tip too.
  return (
    <span className="tag" tabIndex={0} data-tip={tip} aria-label={`${text}. ${tip}`}>
      {text}
    </span>
  )
}

export default function DataQualityBadge({ quality }: { quality: Quality }) {
  const longest = quality.long_gaps.reduce((max, g) => Math.max(max, g.hours), 0)
  const caution = longest > LONG_GAP_HOURS || quality.missing_hours > MANY_MISSING_HOURS

  return (
    <section className="card quality-card">
      <div className={`quality-title ${caution ? 'warn' : 'ok'}`}>
        {caution ? <WarnIcon /> : <CheckIcon />}
        <strong>{caution ? 'Data quality: check gaps' : 'Data quality: good'}</strong>
      </div>
      <div className="tags">
        <Tag text={`Missing ${quality.missing_hours} h`} tip="Hours with no reading at the stations used" />
        <Tag text={`Interpolated ${quality.interpolated_hours} h`} tip="Readings we filled by blending the hours before and after." />
        <Tag
          text={`Longest gap ${longest} h`}
          tip="Longest run of consecutive missing hours"
        />
      </div>
    </section>
  )
}
