import { useEffect, useRef, useState } from 'react'
import { usePrefersReducedMotion } from './usePrefersReducedMotion'

const FIRST_MS = 900
const RERUN_MS = 400

// Counts from 0 up to `target` with an ease-out curve. 900 ms the first time, 400 ms when the target or `runKey`
// changes (season, crop, bias). `delayMs` staggers cards. Under reduced motion the final value is returned at once.
export function useCountUp(target: number, runKey: string, delayMs = 0): number {
  const reduced = usePrefersReducedMotion()
  const [value, setValue] = useState(0)
  const ran = useRef(false)

  useEffect(() => {
    if (reduced) return
    const duration = ran.current ? RERUN_MS : FIRST_MS
    ran.current = true
    const t0 = performance.now() + delayMs
    let raf = 0
    const tick = (now: number) => {
      const p = Math.min(1, Math.max(0, (now - t0) / duration))
      setValue(target * (1 - (1 - p) ** 3))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, runKey, delayMs, reduced])

  return reduced ? target : value
}
