import { useMediaQuery } from './useMediaQuery'

// True when the visitor asked the OS for less motion. Animations check this and show the end state instead.
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery('(prefers-reduced-motion: reduce)')
}
