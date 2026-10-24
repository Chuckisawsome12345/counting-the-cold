import { useEffect, useState } from 'react'
import { fetchStations } from './api/client'
import type { Station } from './api/types'
import CorrectionInfo from './components/CorrectionInfo'
import DataQualityBadge from './components/DataQualityBadge'
import ForecastChart from './components/ForecastChart'
import Header, { type Tab } from './components/Header'
import MapPicker, { DEMO_PINS } from './components/MapPicker'
import SeasonChart from './components/SeasonChart'
import SettingsBar from './components/SettingsBar'
import SummaryCards from './components/SummaryCards'
import ValidationPanel from './components/ValidationPanel'
import { usePoint } from './hooks/usePoint'
import { useTheme } from './hooks/useTheme'
import { DEFAULT_SETTINGS, type Settings } from './settings'

export default function App() {
  const { toggle: toggleTheme } = useTheme()
  const [tab, setTab] = useState<Tab>('orchard')
  const [pin, setPin] = useState<[number, number]>([DEMO_PINS[0].lat, DEMO_PINS[0].lon])
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS)
  const [stations, setStations] = useState<Station[]>([])
  const { data, error, loading } = usePoint({ lat: pin[0], lon: pin[1], ...settings })

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
            <MapPicker pin={pin} stations={stations} onPick={(lat, lon) => setPin([lat, lon])} />
            <div className="demo-pins">
              {DEMO_PINS.map((p) => (
                <button key={p.id} onClick={() => setPin([p.lat, p.lon])}>
                  {p.label}
                </button>
              ))}
            </div>
          </aside>
          <section className="right">
            <SettingsBar season={settings.season} onSeason={(season) => setSettings((s) => ({ ...s, season }))} />
            {error && <div className="banner error">Couldn't load data: {error}</div>}
            {loading && !data && <div className="banner">Loading…</div>}
            {data && (
              <>
                <SummaryCards data={data} />
                <SeasonChart data={data} />
                {data.forecast && <ForecastChart data={data} />}
                <DataQualityBadge quality={data.quality} />
                <CorrectionInfo correction={data.correction} />
              </>
            )}
          </section>
        </main>
      )}
    </div>
  )
}
