import { Rectangle } from 'react-leaflet'
import type { GridResponse } from '../api/client'
import { chillColour, gridRange } from '../chill'

// One tinted square per grid cell, under the station markers and the pin. Not interactive, so map clicks still pick a pin.
export default function ChillLayer({ grid }: { grid: GridResponse }) {
  const [min, max] = gridRange(grid)
  const half = grid.step_deg / 2
  return (
    <>
      {grid.cells.map((c) => (
        <Rectangle
          key={`${c.lat},${c.lon}`}
          bounds={[
            [c.lat - half, c.lon - half],
            [c.lat + half, c.lon + half],
          ]}
          interactive={false}
          pathOptions={{ stroke: false, fillColor: chillColour(max > min ? (c.value - min) / (max - min) : 0.5), fillOpacity: 0.55 }}
        />
      ))}
    </>
  )
}
