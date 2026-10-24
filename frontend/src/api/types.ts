// Mirrors backend/app/schemas.py and docs/api-contract.md.
// Change only through a `contract` PR (see docs/CONTRIBUTING.md).

export type Metric = 'chill_portions' | 'chill_hours' | 'utah_units' | 'gdd'

export type Totals = Record<Metric, number>

export interface Location {
  lat: number
  lon: number
  grid_lat: number
  grid_lon: number
}

export interface SeasonInfo {
  label: string // "2025-26"
  portions_start: string // ISO dates
  hours_start: string
  gdd_start: string
  end: string
  as_of: string
  complete: boolean
}

export interface PointSettings {
  crop: string
  gdd_base_f: number
  gdd_upper_f: number | null
  corrected: boolean
}

// Metric values are cumulative season-to-date (0 before each metric's start date).
export interface DailyRow extends Totals {
  date: string
  tmin: number | null
  tmax: number | null
  source: 'archive' | 'forecast'
  filled: boolean
}

export interface Forecast {
  daily: DailyRow[]
  plus7: Totals
  plus14: Totals
}

export interface HistoryPoint extends Totals {
  day: number // days since Sep 1 of that season
}

export interface HistorySeason {
  season: string
  totals: Totals
  cumulative: HistoryPoint[]
}

export interface Percentiles {
  p10: number
  p50: number
  p90: number
}

export type Climatology = Record<Metric, Percentiles>

export interface GapSpan {
  start: string
  end: string
  hours: number
}

export interface Quality {
  missing_hours: number
  interpolated_hours: number
  long_gaps: GapSpan[]
  stale: boolean
}

export interface StationRef {
  id: number
  name: string
  active: boolean
  distance_km: number
}

export interface CorrectionStation extends StationRef {
  weight: number
}

export interface Correction {
  applied: boolean
  stations: CorrectionStation[]
  expected_error: Totals | null
}

export interface PointResponse {
  mock: boolean
  location: Location
  season: SeasonInfo
  settings: PointSettings
  totals: Totals
  daily: DailyRow[]
  forecast: Forecast | null // null once the season is over
  history: HistorySeason[] // the 10 seasons before this one, oldest first
  climatology: Climatology | null // end-of-season range; null once the season is over
  quality: Quality
  correction: Correction
  nearest_station: StationRef
}

export interface MetricError {
  raw_mae: number
  corrected_mae: number
}

export interface Station {
  id: number
  name: string
  city: string
  county: string
  lat: number
  lon: number
  elevation_ft: number
  active: boolean
  connect_date: string
  disconnect_date: string | null
  group: 'core' | 'durham' | 'durham-neighbor'
  validation: Partial<Record<Metric, MetricError>> | null
}

export interface StationsResponse {
  stations: Station[]
}

export interface SeasonValidation {
  season: string
  cimis: Totals
  raw: Totals
  corrected: Totals
}

export interface StationValidation {
  id: number
  name: string
  seasons: SeasonValidation[]
  mae: Partial<Record<Metric, MetricError>>
}

export interface ValidationResponse {
  built_at: string | null
  summary: Partial<Record<Metric, MetricError>>
  stations: StationValidation[]
}

export interface Crop {
  id: string
  label: string
  base_f: number
  upper_f: number | null
}

// GET /api/telegram/preview: the Telegram bot's reply to one message.
export interface BotPreviewResponse {
  text: string // plain text with line breaks
  bot_url: string | null // the real bot in Telegram; null when the bot isn't configured
}
