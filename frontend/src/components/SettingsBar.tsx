import { SEASONS } from '../settings'

interface Props {
  season: number
  onSeason: (season: number) => void
}

// TODO(C): crop preset (from /api/crops), the three start dates, and the bias-corrected toggle.
export default function SettingsBar({ season, onSeason }: Props) {
  return (
    <div className="settings">
      <label>
        Season{' '}
        <select value={season} onChange={(e) => onSeason(Number(e.target.value))}>
          {SEASONS.map((s) => (
            <option key={s} value={s}>
              {s}-{String(s + 1).slice(2)}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}
