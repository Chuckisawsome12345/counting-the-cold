import { useEffect, useState } from 'react'
import { fetchStations } from './api/client'
import type { Metric, Station } from './api/types'
import CorrectionInfo from './components/CorrectionInfo'
import DataQualityBadge from './components/DataQualityBadge'
import Header, { type Tab } from './components/Header'
import { WarnIcon } from './components/icons'
import MapPicker from './components/MapPicker'
import SeasonChart from './components/SeasonChart'
import SeasonTotals from './components/SeasonTotals'
import SettingsBar from './components/SettingsBar'
import SummaryCards from './components/SummaryCards'
import { ErrorCard, LastNumbersBanner, LoadingSkeleton, StaleBanner } from './components/StatusBanners'
import ValidationPanel from './components/ValidationPanel'
import { DEMO_PINS } from './demoPins'
import { inCalifornia } from './geo'
import { usePoint } from './hooks/usePoint'
import { useTheme } from './hooks/useTheme'
import { DEFAULT_SETTINGS, type Settings } from './settings'

export default function App() {
  const { toggle: toggleTheme } = useTheme()
  const [tab, setTab] = useState<Tab>('orchard')
  const [pin, setPin] = useState<[number, number]>([DEMO_PINS[0].lat, DEMO_PINS[0].lon])
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS)
  const [stations, setStations] = useState<Station[]>([])
  const [metric, setMetric] = useState<Metric>('chill_portions')
  const [locateMessage, setLocateMessage] = useState<string | null>(null)
  const insideCalifornia = inCalifornia(pin[0], pin[1])
  // No request for pins outside California: the API would answer 422.
  const { data, error, loading, reload, requestId } = usePoint(insideCalifornia ? { lat: pin[0], lon: pin[1], ...settings } : null)
  // "Show last saved numbers" applies to one failed request; a new request shows the error card again if it fails.
  const [showLastFor, setShowLastFor] = useState<string | null>(null)
  const showLast = showLastFor === requestId
  const showErrorCard = error !== null && !(showLast && data !== null)
  const stale = data?.quality.stale === true && !error

  const pick = (lat: number, lon: number) => {
    setLocateMessage(null)
    setPin([lat, lon])
  }

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
      <Header tab={tab} onTab={setTab} mock={data?.mock === true} onToggleTheme={toggleTheme} onLocate={locate} />

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
            {insideCalifornia && stale && <StaleBanner onRefresh={reload} />}
            {insideCalifornia && showErrorCard && error && (
              <ErrorCard error={error} hasLast={data !== null} onRetry={reload} onShowLast={() => setShowLastFor(requestId)} />
            )}
            {insideCalifornia && error && showLast && data && <LastNumbersBanner onRetry={reload} />}
            {insideCalifornia && loading && !data && <LoadingSkeleton lat={pin[0]} lon={pin[1]} />}
            {insideCalifornia && data && !showErrorCard && (
              <div className={`right-stack${loading ? ' busy' : ''}`} aria-busy={loading}>
                <SummaryCards data={data} />
                <SeasonChart data={data} metric={metric} onMetric={setMetric} />
                <div className="split">
                  <SeasonTotals data={data} metric={metric} />
                  <div className="stack">
                    <DataQualityBadge quality={data.quality} />
                    <CorrectionInfo correction={data.correction} />
                  </div>
                </div>
              </div>
            )}
          </section>
        </main>
      )}
    </div>
  )
}
