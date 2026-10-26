import { useCallback, useEffect, useState } from 'react'
import { fetchPoint, servedOffline, type PointParams } from '../api/client'
import type { PointResponse } from '../api/types'

// Loads /api/point. The last good response stays in `data` while a new request runs or after it fails, so the
// page can dim it (loading) or offer "show last saved numbers" (error). `reload` re-runs the same request.
export function usePoint(params: PointParams | null) {
  const [data, setData] = useState<PointResponse | null>(null)
  // The outcome of the most recent request to finish; loading and error are derived from it below.
  const [settled, setSettled] = useState<{ id: string; error: Error | null } | null>(null)
  const [attempt, setAttempt] = useState(0)
  const key = params ? JSON.stringify(params) : null
  // Identifies one request, so UI state tied to an error ("show last numbers") resets when a new request starts.
  const requestId = `${key}#${attempt}`

  useEffect(() => {
    if (!key) return
    let cancelled = false
    const id = `${key}#${attempt}`
    fetchPoint(JSON.parse(key) as PointParams)
      .then((d) => {
        if (cancelled) return
        setData(d)
        setSettled({ id, error: null })
      })
      .catch((e: Error) => !cancelled && setSettled({ id, error: e }))
    return () => {
      cancelled = true
    }
  }, [key, attempt])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])

  const current = settled?.id === requestId
  const loading = key !== null && !current
  const error = current ? settled.error : null
  // True when `data` is a saved copy served because there is no signal.
  const offline = data !== null && servedOffline.has(data)

  return { data, error, loading, offline, reload, requestId }
}
