import { useEffect, useState } from 'react'
import { fetchGrid, type GridResponse } from '../api/client'

type Result = { season: number; data: GridResponse | null }

// Loads /api/grid for the statewide chill layer, only while the layer is switched on. `data` is null when the grid
// could not be loaded; an unbuilt grid comes back as a response with no cells.
export function useGrid(enabled: boolean, season: number) {
  const [result, setResult] = useState<Result | null>(null)

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    fetchGrid(season)
      .then((data) => !cancelled && setResult({ season, data }))
      .catch(() => !cancelled && setResult({ season, data: null }))
    return () => {
      cancelled = true
    }
  }, [enabled, season])

  const ready = enabled && result?.season === season
  return { loading: enabled && !ready, grid: ready ? result.data : null, failed: ready && result.data === null }
}
