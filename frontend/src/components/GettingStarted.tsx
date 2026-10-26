import { useEffect, useRef } from 'react'

interface Props {
  onClose: () => void
}

const STEPS = [
  {
    title: 'Put a pin on your orchard',
    text: 'Tap your orchard on the map, use the location button at the top, or try one of the example orchards under the map.',
  },
  {
    title: 'Pick your crop',
    text: 'In "Will my trees bloom on time?", choose almond, pistachio, walnut or prune. We compare your orchard\'s winter chill with what that crop needs.',
  },
  {
    title: 'Follow the steps',
    text: 'Green means bloom should be on time. Amber means watch closely, and red means act. Each comes with what to do next and when.',
  },
]

// First-visit guide: three steps from pin to plan. Closes on the button, Escape, or a click outside.
export default function GettingStarted({ onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="guide-backdrop" onClick={onClose}>
      <div
        className="guide card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-title"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="lbl">How it works</span>
        <h2 id="guide-title">Will your trees bloom on time?</h2>
        <p className="guide-intro">
          Fruit and nut trees need enough winter cold ("chill") to bloom well. In three steps, see whether your orchard is
          getting enough, and what to do if it isn't.
        </p>
        <ol className="guide-steps">
          {STEPS.map((s, i) => (
            <li key={s.title}>
              <span className="guide-num" aria-hidden="true">
                {i + 1}
              </span>
              <div>
                <strong>{s.title}</strong>
                <p>{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
        <button ref={closeRef} type="button" className="chip primary guide-go" onClick={onClose}>
          Got it, show my orchard
        </button>
      </div>
    </div>
  )
}
