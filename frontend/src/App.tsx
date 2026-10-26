import { useCallback, useEffect, useState } from 'react'
import { fetchStations } from './api/client'
import type { Metric, Station } from './api/types'
import BloomOutlook from './components/BloomOutlook'
import BotPreview from './components/BotPreview'
import CorrectionInfo from './components/CorrectionInfo'
import DataQualityBadge from './components/DataQualityBadge'
import GettingStarted from './components/GettingStarted'
import Header, { type Tab } from './components/Header'
import { WarnIcon } from './components/icons'
import MapPicker from './components/MapPicker'
import SeasonChart from './components/SeasonChart'
import SeasonTotals from './components/SeasonTotals'
import SettingsBar from './components/SettingsBar'
import SummaryCards from './components/SummaryCards'
import { ErrorCard, LastNumbersBanner, LoadingSkeleton, OfflineBanner, StaleBanner } from './components/StatusBanners'
import ValidationPanel from './components/ValidationPanel'
import { DEMO_PINS } from './demoPins'
import { inCalifornia } from './geo'
import { usePoint } from './hooks/usePoint'
import { useTheme } from './hooks/useTheme'
import { firstAvailable } from './metrics'
import { DEFAULT_SETTINGS, saveCrop, savedCrop, SEASONS, type Settings } from './settings'

const GUIDE_KEY = 'ctc-guide-seen'

// The first-visit guide shows once per browser; blocked storage just means it shows again next time.
function guideSeen(): boolean {
  try {
    return localStorage.getItem(GUIDE_KEY) === '1'
  } catch {
    return false
  }
}

const seasonLabel = (s: number) => `${s}-${String(s + 1).slice(2)}`

export default function App() {
  const { toggle: toggleTheme } = useTheme()
  const [tab, setTab] = useState<Tab>('orchard')
  const [pin, setPin] = useState<[number, number]>([DEMO_PINS[0].lat, DEMO_PINS[0].lon])
  const [settings, setSettings] = useState<Settings>(() => ({ ...DEFAULT_SETTINGS, crop: savedCrop() }))
  const [stations, setStations] = useState<Station[]>([])
  const [chosenMetric, setMetric] = useState<Metric | null>(null) // null until a tab is clicked
  const [locateMessage, setLocateMessage] = useState<string | null>(null)
  const [guideOpen, setGuideOpen] = useState(() => !guideSeen())
  const [pinPicks, setPinPicks] = useState(0) // counts pins the user chose, so phones can scroll to the answer
  const insideCalifornia = inCalifornia(pin[0], pin[1])
  // No request for pins outside California: the API would answer 422.
  const { data, error, loading, offline, reload, requestId } = usePoint(insideCalifornia ? { lat: pin[0], lon: pin[1], ...settings } : null)
  // "Show last saved numbers" applies to one failed request; a new request shows the error card again if it fails.
  const [showLastFor, setShowLastFor] = useState<string | null>(null)
  const showLast = showLastFor === requestId
  const showErrorCard = error !== null && !(showLast && data !== null)
  const stale = data?.quality.stale === true && !error
  // Until someone clicks a tab, open on the first measure that has data.
  const metric: Metric = chosenMetric ?? (data ? firstAvailable(data) : 'chill_portions')

  const pick = (lat: number, lon: number) => {
    setLocateMessage(null)
    setPin([lat, lon])
    setPinPicks((n) => n + 1)
  }

  const closeGuide = useCallback(() => {
    setGuideOpen(false)
    try {
      localStorage.setItem(GUIDE_KEY, '1')
    } catch {
      // Not remembered; it shows again next visit.
    }
  }, [])

  // "Use my location": the phone's position becomes the pin, like a map click would.
  const locate = () => {
    if (!navigator.geolocation) {
      setLocateMessage("This browser can't share your location. Tap the map to place the pin.")
      return
    }
    navigator.geolocation.getCurrentPosition(
      (p) => pick(Number(p.coords.latitude.toFixed(4)), Number(p.coords.longitude.toFixed(4))),
      () => setLocateMessage("Couldn't get your location. Allow location access, or tap the map to place the pin."),
      { timeout: 10_000 },
    )
  }

  useEffect(() => {
    fetchStations()
      .then((r) => setStations(r.stations))
      .catch(() => setStations([]))
  }, [])

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <Header tab={tab} onTab={setTab} mock={data?.mock === true} onToggleTheme={toggleTheme} onLocate={locate} onHelp={() => setGuideOpen(true)} />
      {guideOpen && <GettingStarted onClose={closeGuide} />}

      {tab === 'orchard' && insideCalifornia && offline && data && (
        <div className="top-banner">
          <OfflineBanner asOf={data.season.as_of} onRetry={reload} />
        </div>
      )}

      {tab === 'accuracy' ? (
        <main className="page" id="main">
          <ValidationPanel stations={stations} />
        </main>
      ) : (
        <main className="layout" id="main">
          <aside className="left">
            <MapPicker
              pin={pin}
              stations={stations}
              nearest={insideCalifornia && !loading ? (data?.nearest_station ?? null) : null}
              season={settings.season}
              onPick={pick}
            />
          </aside>
          <section className="right">
            <SettingsBar settings={settings} onChange={(patch) => setSettings((s) => ({ ...s, ...patch }))} />
            {locateMessage && (
              <div className="banner warn" role="status">
                <WarnIcon size={20} />
                <span className="banner-text">{locateMessage}</span>
              </div>
            )}
            {!insideCalifornia && (
              <div className="notice-dashed" role="status">
                <strong>Pin outside California</strong>
                <span>We only cover California orchards. Move the pin inside the state outline.</span>
              </div>
            )}
            {insideCalifornia && stale && !offline && <StaleBanner onRefresh={reload} />}
            {insideCalifornia && showErrorCard && error && (
              <ErrorCard error={error} hasLast={data !== null} onRetry={reload} onShowLast={() => setShowLastFor(requestId)} />
            )}
            {insideCalifornia && error && showLast && data && <LastNumbersBanner onRetry={reload} />}
            {insideCalifornia && loading && !data && <LoadingSkeleton lat={pin[0]} lon={pin[1]} />}
            {insideCalifornia && data && !showErrorCard && (
              <div className={`right-stack${loading ? ' busy' : ''}`} aria-busy={loading}>
                <BloomOutlook
                  data={data}
                  crop={settings.crop}
                  onCrop={(crop) => {
                    saveCrop(crop)
                    setSettings((s) => ({ ...s, crop }))
                  }}
                  live={settings.season === SEASONS[0] ? null : seasonLabel(SEASONS[0])}
                  revealKey={pinPicks}
                />
                <SummaryCards data={data} />
                <SeasonChart data={data} metric={metric} onMetric={setMetric} />
                <div className="split">
                  <SeasonTotals data={data} metric={metric} />
                  <div className="stack">
                    <DataQualityBadge quality={data.quality} />
                    <CorrectionInfo correction={data.correction} requested={settings.corrected} />
                  </div>
                </div>
              </div>
            )}
            <BotPreview pin={insideCalifornia ? pin : null} />
          </section>
        </main>
      )}
    </div>
  )
}
