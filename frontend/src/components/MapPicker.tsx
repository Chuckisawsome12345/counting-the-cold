import L from 'leaflet'
import { useEffect, useMemo, useState } from 'react'
import { MapContainer, Marker, TileLayer, Tooltip, ZoomControl, useMap, useMapEvents } from 'react-leaflet'
import type { Station, StationRef } from '../api/types'
import { DEMO_PINS } from '../demoPins'
import { formatDate, haversineKm } from '../geo'
import { usePrefersReducedMotion } from '../hooks/usePrefersReducedMotion'

const CALIFORNIA_CENTER: [number, number] = [37.6, -120.5]
const CALIFORNIA_BOUNDS: L.LatLngBoundsExpression = [
  [32.4, -124.5],
  [42.1, -114.1],
]
const PIN_ZOOM = 9
const FLY_SECONDS = 1.2

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)
}

// Station marker: a dot plus a permanent "Name #id" label. Closed stations are hollow with a dashed border.
function stationIcon(s: Station) {
  const size = s.active ? 12 : 15
  return L.divIcon({
    className: s.active ? 'ctc-station' : 'ctc-station closed',
    html: `<span class="st-dot"></span><span class="st-name">${escapeHtml(s.name)} #${s.id}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

// User pin: a teardrop above the point, with a pulsing ring centred on the point.
const PIN_ICON = L.divIcon({
  className: 'ctc-pin',
  html:
    '<span class="pin-ring"></span>' +
    '<svg class="pin-svg" width="28" height="38" viewBox="0 0 28 38" aria-hidden="true">' +
    '<path d="M14 36C14 36 2 22 2 13.5a12 12 0 0 1 24 0C26 22 14 36 14 36z"/>' +
    '<circle cx="14" cy="13.5" r="4.5"/></svg>',
  iconSize: [46, 46],
  iconAnchor: [23, 23],
})

function ClickToPick({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click: (e) => onPick(Number(e.latlng.lat.toFixed(4)), Number(e.latlng.lng.toFixed(4))),
  })
  return null
}

// Fly in to the pin (or out to all of California). Reduced motion jumps instead.
function MapFlight({ pin, showAll }: { pin: [number, number] | null; showAll: boolean }) {
  const map = useMap()
  const reduced = usePrefersReducedMotion()
  const lat = pin?.[0]
  const lon = pin?.[1]
  useEffect(() => {
    if (showAll || lat == null || lon == null) {
      if (reduced) map.fitBounds(CALIFORNIA_BOUNDS, { animate: false })
      else map.flyToBounds(CALIFORNIA_BOUNDS, { duration: FLY_SECONDS })
    } else if (reduced) {
      map.setView([lat, lon], PIN_ZOOM, { animate: false })
    } else {
      map.flyTo([lat, lon], PIN_ZOOM, { duration: FLY_SECONDS })
    }
  }, [map, reduced, lat, lon, showAll])
  return null
}

interface Props {
  pin: [number, number] | null
  stations: Station[]
  nearest: StationRef | null // nearest station for the current pin, once the API has answered
  onPick: (lat: number, lon: number) => void
}

export default function MapPicker({ pin, stations, nearest, onPick }: Props) {
  // "Show all stations" applies to one pin; picking a new pin flies back in.
  const icons = useMemo(() => new Map(stations.map((s) => [s.id, stationIcon(s)])), [stations])
  const pinKey = pin ? `${pin[0]},${pin[1]}` : ''
  const [showAllFor, setShowAllFor] = useState<string | null>(null)
  const showAll = showAllFor === pinKey

  const demo = pin ? DEMO_PINS.find((p) => p.lat === pin[0] && p.lon === pin[1]) : undefined
  const closedStation = nearest && !nearest.active ? stations.find((s) => s.id === nearest.id) : undefined
  const summary = pin
    ? `Map with a pin at ${pin[0]}, ${pin[1]}.` +
      (nearest ? ` Nearest station: ${nearest.name} #${nearest.id}, ${nearest.distance_km} km away${nearest.active ? '' : ', closed'}.` : '')
    : 'Map of California. No pin yet.'

  return (
    <>
      <div className="map-card" role="region" aria-label={summary}>
        <MapContainer center={CALIFORNIA_CENTER} zoom={6} className="map" zoomControl={false}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ZoomControl position="bottomleft" />
          <ClickToPick onPick={onPick} />
          <MapFlight pin={pin} showAll={showAll} />
          {stations.map((s) => (
            <Marker key={s.id} position={[s.lat, s.lon]} icon={icons.get(s.id)} keyboard={false}>
              <Tooltip direction="top" offset={[0, -8]}>
                {s.name} #{s.id} ·{' '}
                {s.active
                  ? `Active${pin ? ` · ${Math.round(haversineKm(pin, [s.lat, s.lon]))} km away` : ''}`
                  : `closed ${s.disconnect_date ? formatDate(s.disconnect_date) : ''}`}
              </Tooltip>
            </Marker>
          ))}
          {pin && (
            <Marker key={pinKey} position={pin} icon={PIN_ICON} keyboard={false}>
              {!showAll && (
                <Tooltip permanent direction="right" offset={[30, -18]} className="pin-info">
                  <span className="pin-coords">
                    {pin[0].toFixed(2)}, {pin[1].toFixed(2)}
                  </span>
                  {demo && <span className="pin-place">{demo.label}</span>}
                  {nearest && <span className="pin-near">Nearest station {nearest.distance_km} km</span>}
                </Tooltip>
              )}
            </Marker>
          )}
        </MapContainer>

        <div className="map-controls">
          {pin && (
            <button type="button" className="chip" onClick={() => setShowAllFor(showAll ? null : pinKey)}>
              <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
                <circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" strokeWidth="1.5" />
                <circle cx="7" cy="7" r="1.6" fill="currentColor" />
              </svg>
              {showAll ? 'Fly to pin' : 'Show all stations'}
            </button>
          )}
          {nearest && !nearest.active && (
            <span className="closed-badge">
              <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
                <path d="M2 2l6 6M8 2L2 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
              {nearest.name} #{nearest.id} closed
              {closedStation?.disconnect_date && <span className="t-long"> {formatDate(closedStation.disconnect_date)}</span>}
            </span>
          )}
        </div>

        <div className="map-legend">
          <span>
            <i className="lg-dot" aria-hidden="true" />
            Active station
          </span>
          <span>
            <i className="lg-dot closed" aria-hidden="true" />
            Closed station
          </span>
        </div>
      </div>

      {pin && (
        <p className="map-caption">
          {pin[0].toFixed(2)}, {pin[1].toFixed(2)}
          {nearest ? ` · ${nearest.distance_km} km` : ''}
        </p>
      )}

      <div className="demo-pins">
        <span className="lbl">Try</span>
        {DEMO_PINS.map((p) => (
          <button key={p.id} type="button" className="chip" aria-pressed={demo?.id === p.id} onClick={() => onPick(p.lat, p.lon)}>
            <span className="t-long">{p.label}</span>
            <span className="t-short">{p.short}</span>
          </button>
        ))}
      </div>
    </>
  )
}
