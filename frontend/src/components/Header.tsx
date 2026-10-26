export type Tab = 'orchard' | 'accuracy'

interface Props {
  tab: Tab
  onTab: (tab: Tab) => void
  mock: boolean
  onToggleTheme: () => void
  onLocate: () => void
  onHelp: () => void
}

const TABS: { id: Tab; label: string }[] = [
  { id: 'orchard', label: 'Orchard' },
  { id: 'accuracy', label: 'How accurate is this?' },
]

function Logo() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" role="img" aria-label="Counting the Cold logo">
      <defs>
        <linearGradient id="ctc-logo-grad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="var(--cold4)" />
          <stop offset=".5" stopColor="var(--cold3)" />
          <stop offset=".5" stopColor="var(--heat1)" />
          <stop offset="1" stopColor="var(--heat3)" />
        </linearGradient>
      </defs>
      <circle cx="20" cy="20" r="16" fill="none" stroke="url(#ctc-logo-grad)" strokeWidth="3.5" />
      <path
        d="M20 9v22M11 14l18 12M29 14L11 26"
        stroke="url(#ctc-logo-grad)"
        strokeWidth="2"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  )
}

function SunIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="4" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M10 1.5v2.5M10 16v2.5M1.5 10H4M16 10h2.5M4 4l1.8 1.8M14.2 14.2L16 16M4 16l1.8-1.8M14.2 5.8L16 4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  )
}

export function MockBadge() {
  return (
    <span className="mock-badge" title="Development data. Numbers are synthetic.">
      <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
        <path d="M6 1l5.5 10h-11z" fill="none" stroke="currentColor" strokeWidth="1.4" />
      </svg>
      <span className="t-long">SYNTHETIC MOCK DATA</span>
      <span className="t-short">MOCK</span>
    </span>
  )
}

function LocateIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="4.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="10" cy="10" r="1.4" fill="currentColor" />
      <path d="M10 1.5v3M10 15.5v3M1.5 10h3M15.5 10h3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

function HelpIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M7.6 7.6a2.5 2.5 0 1 1 3.4 2.3c-.6.3-1 .8-1 1.5v.4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="10" cy="14.6" r="1" fill="currentColor" />
    </svg>
  )
}

export default function Header({ tab, onTab, mock, onToggleTheme, onLocate, onHelp }: Props) {
  return (
    <>
      <header className="header">
        <div className="brand">
          <Logo />
          <div>
            <h1>Counting the Cold</h1>
            <p className="tagline">Your orchard's chill and heat, not a station's.</p>
          </div>
        </div>
        <nav className="tabs" aria-label="Views">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={tab === t.id ? 'active' : ''}
              aria-current={tab === t.id ? 'page' : undefined}
              onClick={() => onTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="header-end">
          {mock && <MockBadge />}
          <button type="button" className="icon-btn" aria-label="How it works" title="How it works" onClick={onHelp}>
            <HelpIcon />
          </button>
          <button type="button" className="icon-btn locate-btn" aria-label="Use my location" onClick={onLocate}>
            <LocateIcon />
          </button>
          <button
            type="button"
            className="icon-btn"
            aria-label="Switch light or dark theme"
            onClick={onToggleTheme}
          >
            <SunIcon />
          </button>
        </div>
      </header>
      <div className="header-rule" aria-hidden="true" />
    </>
  )
}
