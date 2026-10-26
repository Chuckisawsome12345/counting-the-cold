import { SEASONS, type Settings } from '../settings'

interface Props {
  settings: Settings
  onChange: (patch: Partial<Settings>) => void
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
// Days per month for the day picker; Feb allows the 29th because the season windows handle leap years.
const DAYS_IN_MONTH = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
const OLDER_SEASONS = SEASONS.filter((s) => s < 2025)

function seasonLabel(s: number) {
  return `${s}-${String(s + 1).slice(2)}`
}

function DateField({ label, value, onChange }: { label: string; value: string; onChange: (mmdd: string) => void }) {
  const [m, d] = value.split('-').map(Number)
  const pad = (n: number) => String(n).padStart(2, '0')
  const setMonth = (month: number) => onChange(`${pad(month)}-${pad(Math.min(d, DAYS_IN_MONTH[month - 1]))}`)
  return (
    <div className="field">
      <span className="lbl">{label} from</span>
      <div className="date-field" role="group" aria-label={`${label} start date`}>
        <select aria-label={`${label} start month`} value={m} onChange={(e) => setMonth(Number(e.target.value))}>
          {MONTHS.map((name, i) => (
            <option key={name} value={i + 1}>
              {name}
            </option>
          ))}
        </select>
        <select aria-label={`${label} start day`} value={d} onChange={(e) => onChange(`${pad(m)}-${pad(Number(e.target.value))}`)}>
          {Array.from({ length: DAYS_IN_MONTH[m - 1] }, (_, i) => i + 1).map((day) => (
            <option key={day} value={day}>
              {day}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}

export default function SettingsBar({ settings, onChange }: Props) {
  const olderSelected = settings.season < 2025

  return (
    <div className="card settings" role="group" aria-label="Season and start-date settings">
      <div className="field">
        <span className="lbl">Season</span>
        <div className="field-row">
          <div className="seg" role="group" aria-label="Season">
            <button type="button" aria-pressed={settings.season === 2025} onClick={() => onChange({ season: 2025 })}>
              {seasonLabel(2025)}
            </button>
            <button
              type="button"
              aria-pressed={settings.season === 2026}
              title="In progress"
              onClick={() => onChange({ season: 2026 })}
            >
              {seasonLabel(2026)}
              <span className="live-tag">live</span>
            </button>
          </div>
          <select
            aria-label="Older season"
            value={olderSelected ? settings.season : ''}
            onChange={(e) => e.target.value && onChange({ season: Number(e.target.value) })}
          >
            <option value="">Older…</option>
            {OLDER_SEASONS.map((s) => (
              <option key={s} value={s}>
                {seasonLabel(s)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="field-row dates">
        <DateField label="Chill portions" value={settings.portions_start} onChange={(v) => onChange({ portions_start: v })} />
        <DateField label="Chill hours" value={settings.hours_start} onChange={(v) => onChange({ hours_start: v })} />
        <DateField label="GDD" value={settings.gdd_start} onChange={(v) => onChange({ gdd_start: v })} />
        <button
          type="button"
          role="switch"
          aria-checked={settings.corrected}
          className="switch-row"
          onClick={() => onChange({ corrected: !settings.corrected })}
        >
          <span className="switch" aria-hidden="true" />
          <span>
            Bias-corrected <span className="state">{settings.corrected ? 'on' : 'off'}</span>
          </span>
        </button>
      </div>
    </div>
  )
}
