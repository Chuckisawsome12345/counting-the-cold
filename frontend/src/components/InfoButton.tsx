import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { NARROW_QUERY, useMediaQuery } from '../hooks/useMediaQuery'

const PANEL_WIDTH = 320
const EDGE = 12 // keep this far from the screen edge
const GAP = 8 // between the button and the popover

interface Props {
  title: string // "Chill portions"
  text: string // the explanation, one short body from metricInfo.ts
  footer?: string // an optional small line under the body
  ariaLabel?: string // overrides the default "About <title>" label on the button
  live?: string // one line from the card's own values; left out when there is none
  accent: 'cold' | 'heat'
  open: boolean
  onToggle: () => void
  onClose: () => void
}

// A small "i" that opens a short explanation. A popover under the button on desktop, a bottom sheet on phones. Opens by
// click, tap, Enter or Space (never hover); closes on Escape, a second click, or a click outside.
export default function InfoButton({ title, text, footer, ariaLabel, live, accent, open, onToggle, onClose }: Props) {
  const id = useId()
  const panelId = `info-panel-${id}`
  const titleId = `info-title-${id}`
  const buttonRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)
  const narrow = useMediaQuery(NARROW_QUERY)
  const [place, setPlace] = useState<CSSProperties>({})

  // Desktop: sit under the button, inside the screen, and flip above it when there is no room below.
  useLayoutEffect(() => {
    if (!open || narrow) return
    const update = () => {
      const button = buttonRef.current
      if (!button) return
      const r = button.getBoundingClientRect()
      const width = Math.min(PANEL_WIDTH, window.innerWidth - EDGE * 2)
      const left = Math.min(Math.max(r.left + r.width / 2 - width / 2, EDGE), window.innerWidth - width - EDGE)
      const below = window.innerHeight - r.bottom - GAP - EDGE
      const above = r.top - GAP - EDGE
      setPlace(
        below >= 230 || below >= above
          ? { left, width, top: r.bottom + GAP, maxHeight: Math.max(below, 160) }
          : { left, width, bottom: window.innerHeight - r.top + GAP, maxHeight: Math.max(above, 160) },
      )
    }
    update()
    window.addEventListener('resize', update)
    window.addEventListener('scroll', update, true)
    return () => {
      window.removeEventListener('resize', update)
      window.removeEventListener('scroll', update, true)
    }
  }, [open, narrow])

  // Close on a click or tap outside, and on Escape (then put focus back on the button).
  useEffect(() => {
    if (!open) return
    const outside = (e: PointerEvent) => {
      const t = e.target as Node
      if (!panelRef.current?.contains(t) && !buttonRef.current?.contains(t)) onClose()
    }
    const escape = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
        buttonRef.current?.focus()
      }
    }
    document.addEventListener('pointerdown', outside)
    document.addEventListener('keydown', escape)
    return () => {
      document.removeEventListener('pointerdown', outside)
      document.removeEventListener('keydown', escape)
    }
  }, [open, onClose])

  // Move focus into the panel when it opens.
  useEffect(() => {
    if (open) closeRef.current?.focus()
  }, [open])

  // The close button is the panel's only control, so Tab stays on it instead of wandering off behind the panel.
  const trapTab = (e: KeyboardEvent) => {
    if (e.key === 'Tab') {
      e.preventDefault()
      closeRef.current?.focus()
    }
  }

  const closeAndRefocus = () => {
    onClose()
    buttonRef.current?.focus()
  }

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="info-btn"
        aria-label={ariaLabel ?? `About ${title.toLowerCase()}`}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={onToggle}
      >
        <span className="info-dot" aria-hidden="true">
          i
        </span>
      </button>

      {open &&
        createPortal(
          <>
            {narrow && <div className="info-backdrop" aria-hidden="true" />}
            <div
              ref={panelRef}
              id={panelId}
              className={`info-panel ${accent}`}
              role="dialog"
              aria-modal={narrow}
              aria-labelledby={titleId}
              style={narrow ? undefined : place}
              onKeyDown={trapTab}
            >
              <div className="info-head">
                <h3 id={titleId}>{title}</h3>
                <button ref={closeRef} type="button" className="info-close" aria-label={`Close ${title.toLowerCase()} explanation`} onClick={closeAndRefocus}>
                  <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
                    <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                  </svg>
                </button>
              </div>
              <div className="info-body">
                {live && <p className="info-live">{live}</p>}
                <p>{text}</p>
                {footer && <p className="info-foot">{footer}</p>}
              </div>
            </div>
          </>,
          document.body,
        )}
    </>
  )
}
