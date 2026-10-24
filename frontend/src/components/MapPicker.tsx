import { CircleMarker, MapContainer, TileLayer, Tooltip, useMapEvents } from 'react-leaflet'
import type { Station } from '../api/types'

export const DEMO_PINS = [
  { id: 'butte-durham', label: 'Butte orchard near Durham', lat: 39.64, lon: -121.79 },
  { id: 'davis', label: 'Davis', lat: 38.5357, lon: -121.7764 },
  { id: 'parlier', label: 'Parlier', lat: 36.5974, lon: -119.504 },
]

const CALIFORNIA_CENTER: [number, number] = [37.6, -120.5]

function ClickToPick({ onPick }: { onPick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click: (e) => onPick(Number(e.latlng.lat.toFixed(4)), Number(e.latlng.lng.toFixed(4))),
  })
  return null
}

interface Props {
  pin: [number, number] | null
  stations: Station[]
  onPick: (lat: number, lon: number) => void
}

// TODO(C): fly to the pin, nicer markers, address search (stretch).
export default function MapPicker({ pin, stations, onPick }: Props) {
  return (
    <MapContainer center={CALIFORNIA_CENTER} zoom={6} className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickToPick onPick={onPick} />
      {stations.map((s) => (
        <CircleMarker
          key={s.id}
          center={[s.lat, s.lon]}
          radius={6}
          pathOptions={
            s.active
              ? { color: '#1f6fb2', fillColor: '#1f6fb2', fillOpacity: 0.9 }
              : { color: '#777', fillOpacity: 0, dashArray: '3' }
          }
        >
          <Tooltip>
            {s.name} #{s.id}
            {s.active ? '' : `, closed ${s.disconnect_date}`}
          </Tooltip>
        </CircleMarker>
      ))}
      {pin && (
        <CircleMarker center={pin} radius={9} pathOptions={{ color: '#b03a2e', fillColor: '#e74c3c', fillOpacity: 0.85 }} />
      )}
    </MapContainer>
  )
}
