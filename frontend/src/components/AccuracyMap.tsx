import { useEffect } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import type { LatLngBoundsExpression } from 'leaflet'
import type { Station, StationValidation } from '../api/types'
import { formatFixed } from '../format'
import type { MetricInfo } from '../metrics'

// Raw error is amber, corrected error is ice blue. Fixed colours so the story reads the same in both themes.
const RAW = { stroke: [232, 98, 12], fill: [255, 168, 28] }
const CORRECTED = { stroke: [27, 143, 214], fill: [79, 180, 240] }

const mix = (a: number[], b: number[], t: number) => `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(',')})`

const MIN_RADIUS = 5
const MAX_RADIUS = 26

export interface AccuracyRow {
  validation: StationValidation
  station: Station
  raw: number
  corrected: number
}

function FitStations({ points }: { points: [number, number][] }) {
  const map = useMap()
  const key = points.map((p) => p.join(',')).join(';')
  useEffect(() => {
    if (points.length) map.fitBounds(points as LatLngBoundsExpression, { padding: [40, 40], maxZoom: 8, animate: false })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, key])
  return null
}

interface Props {
  rows: AccuracyRow[]
  info: MetricInfo
  progress: (i: number) => number
  mode: 'raw' | 'corrected' | null
  onShow: (corrected: boolean) => void
  onPlay: () => void
}

// Each station is a bubble whose area is its error. Raw bubbles are big and amber; corrected ones shrink and turn blue.
export default function AccuracyMap({ rows, info, progress, mode, onShow, onPlay }: Props) {
  const maxError = Math.max(...rows.map((r) => r.raw), 0.0001)
  const radius = (error: number) => MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * Math.sqrt(Math.max(0, error) / maxError)
  // Labels alternate left and right going north to south, so the tight Butte/Colusa cluster stays readable.
  const sides = new Map(
    [...rows].sort((a, b) => b.station.lat - a.station.lat).map((r, i) => [r.station.id, i % 2 === 0 ? 'right' : 'left'] as const),
  )
  const label = `Accuracy map. Bubble size is the error at each of ${rows.length} stations, in ${info.footUnit}.`

  return (
    <section className="card acc-card" role="region" aria-label={label}>
      <div className="acc-head">
        <div>
          <span className="lbl">Accuracy map</span>
          <p className="v-sub">Bubble size is the error at that station.</p>
        </div>
        <div className="acc-controls">
          <div className="seg" role="group" aria-label="Show raw or corrected error">
            <button type="button" aria-pressed={mode === 'raw'} onClick={() => onShow(false)}>
              Raw
            </button>
            <button type="button" aria-pressed={mode === 'corrected'} onClick={() => onShow(true)}>
              Corrected
            </button>
          </div>
          <button type="button" className="chip" onClick={onPlay}>
            <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
              <path d="M2.5 1.5l8 4.5-8 4.5z" fill="currentColor" />
            </svg>
            Play
          </button>
        </div>
      </div>

      <div className="acc-map">
        <MapContainer center={[37.6, -120.5]} zoom={6} zoomControl={false} scrollWheelZoom={false} className="map" keyboard>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitStations points={rows.map((r) => [r.station.lat, r.station.lon])} />
          {rows.map((r, i) => {
            const p = progress(i)
            const closed = !r.station.active
            const value = r.raw + (r.corrected - r.raw) * p
            return (
              <CircleMarker
                key={r.station.id}
                center={[r.station.lat, r.station.lon]}
                radius={radius(value)}
                pathOptions={{
                  color: mix(RAW.stroke, CORRECTED.stroke, p),
                  fillColor: mix(RAW.fill, CORRECTED.fill, p),
                  fillOpacity: 0.4,
                  weight: 2,
                  dashArray: closed ? '4 4' : undefined,
                }}
              >
                <Tooltip
                  permanent
                  direction={sides.get(r.station.id)}
                  offset={[(sides.get(r.station.id) === 'left' ? -1 : 1) * (radius(value) + 2), 0]}
                  className="acc-label"
                >
                  {r.station.name} ±{formatFixed(value, info.digits)}
                  {closed ? ' · closed' : ''}
                </Tooltip>
              </CircleMarker>
            )
          })}
        </MapContainer>
        <div className="acc-legend">
          <span>
            <i className="lg-dot raw" aria-hidden="true" />
            Raw
          </span>
          <span>
            <i className="lg-dot corrected" aria-hidden="true" />
            Corrected
          </span>
        </div>
      </div>
    </section>
  )
}
