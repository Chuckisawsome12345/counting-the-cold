import { useCallback, useEffect, useRef, useState } from 'react'
import { usePrefersReducedMotion } from './usePrefersReducedMotion'

const DURATION_MS = 900 // one bubble shrinking from raw to corrected
const STAGGER_MS = 40 // each bubble starts this long after the one before
const HOLD_MS = 1100 // "Play" holds the raw state this long before shrinking

const ease = (p: number) => 1 - (1 - Math.min(1, Math.max(0, p))) ** 3

// Drives the accuracy map and the headline from raw to corrected error. `t` is a clock in ms: at 0 every bubble is
// raw, at `end` every bubble is corrected, and in between bubble i has moved ease((t - i * STAGGER) / DURATION).
// Under reduced motion the states swap with no transition.
export function useRawToCorrected(count: number) {
  const reduced = usePrefersReducedMotion()
  const end = DURATION_MS + Math.max(0, count - 1) * STAGGER_MS
  const [t, setT] = useState(0)
  const raf = useRef(0)
  const timer = useRef(0)

  const stop = useCallback(() => {
    cancelAnimationFrame(raf.current)
    clearTimeout(timer.current)
  }, [])

  const run = useCallback(() => {
    const t0 = performance.now()
    const tick = (now: number) => {
      const elapsed = Math.min(end, now - t0)
      setT(elapsed)
      if (elapsed < end) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
  }, [end])

  // Hold raw, then shrink to corrected (or just swap, under reduced motion).
  const schedule = useCallback(() => {
    timer.current = window.setTimeout(() => (reduced ? setT(end) : run()), HOLD_MS)
  }, [reduced, end, run])

  const play = useCallback(() => {
    stop()
    setT(0)
    schedule()
  }, [stop, schedule])

  const show = useCallback(
    (corrected: boolean) => {
      stop()
      setT(corrected ? end : 0)
    },
    [stop, end],
  )

  // Play once when the results first appear.
  useEffect(() => {
    schedule()
    return stop
  }, [schedule, stop])

  return {
    /** 0 = raw, 1 = corrected, for the bubble at position `i`. */
    progress: (i: number) => ease((t - i * STAGGER_MS) / DURATION_MS),
    /** The same for the headline number, which moves as a whole. */
    overall: ease(t / end),
    mode: t >= end ? ('corrected' as const) : t === 0 ? ('raw' as const) : null,
    play,
    show,
  }
}
