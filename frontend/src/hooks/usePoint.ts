import { useEffect, useState } from 'react'
import { fetchPoint, type PointParams } from '../api/client'
import type { PointResponse } from '../api/types'

export function usePoint(params: PointParams | null) {
  const [data, setData] = useState<PointResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const key = params ? JSON.stringify(params) : null

  useEffect(() => {
    if (!params) return
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchPoint(params)
      .then((d) => !cancelled && setData(d))
      .catch((e: Error) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [key])

  return { data, error, loading }
}
