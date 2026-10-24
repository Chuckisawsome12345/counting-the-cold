import type { Crop, PointResponse, StationsResponse, ValidationResponse } from './types'
import { MOCK_STATIONS } from './mock/stations'
import { MOCK_VALIDATION } from './mock/validation'
import mockCompleteUrl from './mock/point.json?url'
import mockCurrentUrl from './mock/point_current.json?url'

// Empty in dev: Vite proxies /api to the backend. Set to the Render URL in production.
const API_BASE = import.meta.env.VITE_API_URL ?? ''
// VITE_USE_MOCK=1 serves the synthetic mocks without a backend.
const USE_MOCK = import.meta.env.VITE_USE_MOCK === '1'

export interface PointParams {
  lat: number
  lon: number
  season: number // 2025 = Sep 1 2025 to Aug 31 2026
  crop?: string
  portions_start?: string // "MM-DD"
  hours_start?: string
  gdd_start?: string
  corrected?: boolean
}

// An answer that was not a success. `status` is the HTTP status (503, 502, ...); it is undefined when there was
// no answer at all (network down).
export class ApiError extends Error {
  status?: number
  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// Responses the service worker answered from its saved copy because the network failed (header x-ctc-offline).
// Tracked by object, so the types in types.ts stay untouched.
export const servedOffline = new WeakSet<object>()

async function getJson<T>(url: string): Promise<T> {
  let res: Response
  try {
    res = await fetch(url)
  } catch {
    throw new ApiError(`${url} could not be reached`)
  }
  if (!res.ok) throw new ApiError(`${url} failed: ${res.status}`, res.status)
  const data = (await res.json()) as T
  if (res.headers.get('x-ctc-offline') === '1' && typeof data === 'object' && data !== null) servedOffline.add(data)
  return data
}

export function fetchPoint(params: PointParams): Promise<PointResponse> {
  if (USE_MOCK) return getJson(params.season >= 2026 ? mockCurrentUrl : mockCompleteUrl)
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined) qs.set(k, String(v))
  return getJson(`${API_BASE}/api/point?${qs}`)
}

export function fetchStations(): Promise<StationsResponse> {
  if (USE_MOCK) return Promise.resolve({ stations: MOCK_STATIONS })
  return getJson(`${API_BASE}/api/stations`)
}

export function fetchValidation(): Promise<ValidationResponse> {
  if (USE_MOCK) return Promise.resolve(MOCK_VALIDATION)
  return getJson(`${API_BASE}/api/validation`)
}

// Crop presets. Mock mode (and a failed call, see SettingsBar) falls back to the three standard presets.
export const FALLBACK_CROPS: Crop[] = [
  { id: 'almond', label: 'Almond', base_f: 55, upper_f: 94 },
  { id: 'walnut', label: 'Walnut', base_f: 50, upper_f: 88 },
  { id: 'generic', label: 'Generic', base_f: 50, upper_f: null },
]

export async function fetchCrops(): Promise<Crop[]> {
  if (USE_MOCK) return FALLBACK_CROPS
  return (await getJson<{ crops: Crop[] }>(`${API_BASE}/api/crops`)).crops
}
