import { useCallback, useState } from 'react'

// Which of a group of popovers is open, so only one can be at a time. Opening another closes the first.
export function useSingleOpen() {
  const [openId, setOpenId] = useState<string | null>(null)
  const toggle = useCallback((id: string) => setOpenId((cur) => (cur === id ? null : id)), [])
  const close = useCallback(() => setOpenId(null), [])
  return { openId, toggle, close }
}
