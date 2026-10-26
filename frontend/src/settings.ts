// Settings that drive /api/point. Lifted into App.tsx so every component reads the same values.

export interface Settings {
  season: number // 2025 = Sep 1 2025 to Aug 31 2026
  crop: string // preset id from /api/crops
  portions_start: string // "MM-DD"
  hours_start: string
  gdd_start: string
  corrected: boolean
}

export const DEFAULT_SETTINGS: Settings = {
  season: 2025,
  crop: 'almond',
  portions_start: '09-01',
  hours_start: '11-01',
  gdd_start: '01-01',
  corrected: true,
}

const CROP_KEY = 'ctc-crop'
// Crops the app offers: each has a bloom verdict (bloomAdvice.ts) and a heat preset (/api/crops).
export const CROP_IDS = ['almond', 'pistachio', 'walnut', 'prune'] as const

// The crop chosen on an earlier visit, if any. Storage can be blocked (private windows), so fall back quietly.
export function savedCrop(): string {
  try {
    const saved = localStorage.getItem(CROP_KEY)
    if (saved && (CROP_IDS as readonly string[]).includes(saved)) return saved
  } catch {
    // fall through
  }
  return DEFAULT_SETTINGS.crop
}

export function saveCrop(crop: string) {
  try {
    localStorage.setItem(CROP_KEY, crop)
  } catch {
    // Not remembered; the choice still applies for this visit.
  }
}

export const SEASONS = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016]
