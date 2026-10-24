import { useCallback, useEffect, useState } from 'react'
import { fetchPoint, servedOffline, type PointParams } from '../api/client'
import type { PointResponse } from '../api/types'

// Loads /api/point. The last good response stays in `data` while a new request runs or after it fails, so the
// page can dim it (loading) or offer "show last saved numbers" (error). `reload` re-runs the same request.
export function usePoint(params: PointParams | null) {
  const [data, setData] = useState<PointResponse | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(params !== null)
  const [attempt, setAttempt] = useState(0)
  const key = params ? JSON.stringify(params) : null

  useEffect(() => {
    if (!key) return
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchPoint(JSON.parse(key) as PointParams)
      .then((d) => !cancelled && setData(d))
      .catch((e: Error) => !cancelled && setError(e))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [key, attempt])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])

  // Identifies one request, so UI state tied to an error ("show last numbers") resets when a new request starts.
  // True when `data` is a saved copy served because there is no signal.
  const offline = data !== null && servedOffline.has(data)

  return { data, error, loading, offline, reload, requestId: `${key}#${attempt}` }
}
