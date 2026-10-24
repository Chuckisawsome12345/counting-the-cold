import type { PointResponse, StationsResponse, ValidationResponse } from './types'
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

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} failed: ${res.status}`)
  return (await res.json()) as T
}

export function fetchPoint(params: PointParams): Promise<PointResponse> {
  if (USE_MOCK) return getJson(params.season >= 2026 ? mockCurrentUrl : mockCompleteUrl)
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) if (v !== undefined) qs.set(k, String(v))
  return getJson(`${API_BASE}/api/point?${qs}`)
}

export function fetchStations(): Promise<StationsResponse> {
  if (USE_MOCK) return Promise.resolve({ stations: [] })
  return getJson(`${API_BASE}/api/stations`)
}

export function fetchValidation(): Promise<ValidationResponse> {
  return getJson(`${API_BASE}/api/validation`)
}
