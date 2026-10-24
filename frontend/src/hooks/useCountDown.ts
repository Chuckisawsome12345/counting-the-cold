import { useEffect, useState } from 'react'
import { usePrefersReducedMotion } from './usePrefersReducedMotion'

const DURATION_MS = 900

// Eases from `from` to `to` over 900 ms (the accuracy headline counting down from raw to corrected error).
// Re-runs when `runKey` changes. Under reduced motion the end value is returned at once.
export function useCountDown(from: number, to: number, runKey: string): number {
  const reduced = usePrefersReducedMotion()
  const [value, setValue] = useState(from)

  useEffect(() => {
    if (reduced) return
    const t0 = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / DURATION_MS)
      setValue(from + (to - from) * (1 - (1 - p) ** 3))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [from, to, runKey, reduced])

  return reduced ? to : value
}
