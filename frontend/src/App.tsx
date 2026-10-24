import { useEffect, useState } from 'react'
import { fetchStations } from './api/client'
import type { Metric, Station } from './api/types'
import CorrectionInfo from './components/CorrectionInfo'
import DataQualityBadge from './components/DataQualityBadge'
import Header, { type Tab } from './components/Header'
import MapPicker from './components/MapPicker'
import SeasonChart from './components/SeasonChart'
import SeasonTotals from './components/SeasonTotals'
import SettingsBar from './components/SettingsBar'
import SummaryCards from './components/SummaryCards'
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
  const insideCalifornia = inCalifornia(pin[0], pin[1])
  // No request for pins outside California: the API would answer 422.
  const { data, error, loading } = usePoint(insideCalifornia ? { lat: pin[0], lon: pin[1], ...settings } : null)

  useEffect(() => {
    fetchStations()
      .then((r) => setStations(r.stations))
      .catch(() => setStations([]))
  }, [])

  return (
    <div className="app">
      <Header tab={tab} onTab={setTab} mock={data?.mock === true} onToggleTheme={toggleTheme} />

      {tab === 'accuracy' ? (
        <main className="page">
          <ValidationPanel />
        </main>
      ) : (
        <main className="layout">
          <aside className="left">
            <MapPicker
              pin={pin}
              stations={stations}
              nearest={insideCalifornia && !loading ? (data?.nearest_station ?? null) : null}
              onPick={(lat, lon) => setPin([lat, lon])}
            />
          </aside>
          <section className="right">
            <SettingsBar settings={settings} onChange={(patch) => setSettings((s) => ({ ...s, ...patch }))} />
            {!insideCalifornia && (
              <div className="notice-dashed" role="status">
                <strong>Pin outside California</strong>
                <span>We only cover California orchards. Move the pin inside the state outline.</span>
              </div>
            )}
            {insideCalifornia && error && <div className="banner error">Couldn't load data: {error}</div>}
            {insideCalifornia && loading && !data && <div className="banner">Loading…</div>}
            {insideCalifornia && data && (
              <>
                <SummaryCards data={data} />
                <SeasonChart data={data} metric={metric} onMetric={setMetric} />
                <div className="split">
                  <SeasonTotals data={data} metric={metric} />
                  <div className="stack">
                    <DataQualityBadge quality={data.quality} />
                    <CorrectionInfo correction={data.correction} />
                  </div>
                </div>
              </>
            )}
          </section>
        </main>
      )}
    </div>
  )
}
