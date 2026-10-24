import { useSyncExternalStore } from 'react'

// Re-renders when a CSS media query starts or stops matching. False on the server and before hydration.
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mq = window.matchMedia(query)
      mq.addEventListener('change', onChange)
      return () => mq.removeEventListener('change', onChange)
    },
    () => window.matchMedia(query).matches,
    () => false,
  )
}

// Phone width: matches the 600px breakpoint in index.css.
export const NARROW_QUERY = '(max-width: 600px)'
