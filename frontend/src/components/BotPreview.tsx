import { type FormEvent, useEffect, useRef, useState } from 'react'
import { fetchBotPreview } from '../api/client'

// Orchard chat: ask about a place in plain words. The answers come from the same backend code as the Telegram bot.

interface Message {
  id: number
  from: 'user' | 'bot'
  text: string
  failed?: boolean
}

const MAX_MESSAGES = 6 // the last three exchanges
const QUICK = [
  { label: 'Durham', text: 'durham' },
  { label: 'Davis', text: 'davis' },
  { label: 'Parlier', text: 'parlier' },
  { label: 'Suggestions for Durham', text: '/suggest durham' },
]

// Bot replies are plain text; make the links in them clickable.
function Linked({ text }: { text: string }) {
  return (
    <>
      {text.split(/(https?:\/\/\S+)/).map((part, i) =>
        /^https?:\/\//.test(part) ? (
          <a key={i} href={part} target="_blank" rel="noreferrer">
            {part}
          </a>
        ) : (
          part
        ),
      )}
    </>
  )
}

export default function BotPreview({ pin }: { pin: [number, number] | null }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const nextId = useRef(0)
  const logRef = useRef<HTMLDivElement>(null)

  const add = (m: Omit<Message, 'id'>) => setMessages((ms) => [...ms, { ...m, id: nextId.current++ }].slice(-MAX_MESSAGES))

  // The welcome: how to ask.
  useEffect(() => {
    let live = true // React's dev double-run would otherwise show it twice
    fetchBotPreview('')
      .then((r) => live && add({ from: 'bot', text: r.text }))
      .catch(() => {})
    return () => {
      live = false
    }
  }, [])

  // Keep the newest message in view from its first line: replies are long, and they read top down.
  useEffect(() => {
    const last = logRef.current?.lastElementChild as HTMLElement | null | undefined
    if (logRef.current && last) logRef.current.scrollTop = last.offsetTop - 8
  }, [messages, busy])

  const send = async (text: string) => {
    const t = text.trim()
    if (!t || busy) return
    add({ from: 'user', text: t })
    setDraft('')
    setBusy(true)
    try {
      const r = await fetchBotPreview(t)
      add({ from: 'bot', text: r.text })
    } catch {
      add({ from: 'bot', text: "Couldn't get an answer right now. Try again in a moment.", failed: true })
    } finally {
      setBusy(false)
    }
  }

  const submit = (e: FormEvent) => {
    e.preventDefault()
    void send(draft)
  }

  const pinText = pin ? `${pin[0].toFixed(2)},${pin[1].toFixed(2)}` : null

  return (
    <section className="card bot-card" aria-labelledby="bot-title">
      <div className="bot-head">
        <span className="lbl">Ask</span>
        <h2 id="bot-title">Ask about an orchard</h2>
        <p>Type a place or coordinates and get its chill and heat in plain words, plus what to watch for.</p>
      </div>

      <div className="bot-log" ref={logRef} aria-live="polite">
        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.from}${m.failed ? ' failed' : ''}`}>
            {m.from === 'bot' ? <Linked text={m.text} /> : m.text}
          </div>
        ))}
        {busy && (
          <div className="bubble bot typing" aria-label="Getting an answer">
            <i />
            <i />
            <i />
          </div>
        )}
      </div>

      <div className="bot-quick" role="group" aria-label="Quick messages">
        {pinText && (
          <button type="button" className="chip" disabled={busy} onClick={() => void send(pinText)}>
            This pin ({pinText})
          </button>
        )}
        {QUICK.map((q) => (
          <button key={q.text} type="button" className="chip" disabled={busy} onClick={() => void send(q.text)}>
            {q.label}
          </button>
        ))}
      </div>

      <form className="bot-form" onSubmit={submit}>
        <label className="sr-only" htmlFor="bot-input">
          Ask about a place
        </label>
        <input
          id="bot-input"
          value={draft}
          maxLength={200}
          placeholder="A place or lat,lon, e.g. 39.64,-121.79"
          onChange={(e) => setDraft(e.target.value)}
        />
        <button type="submit" className="chip primary" disabled={busy || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
