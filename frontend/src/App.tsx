import { useEffect, useState } from 'react'
import { fetchStations } from './api/client'
import type { Station } from './api/types'
import CorrectionInfo from './components/CorrectionInfo'
import DataQualityBadge from './components/DataQualityBadge'
import ForecastChart from './components/ForecastChart'
import MapPicker, { DEMO_PINS } from './components/MapPicker'
import SeasonChart from './components/SeasonChart'
import SettingsBar from './components/SettingsBar'
import SummaryCards from './components/SummaryCards'
import ValidationPanel from './components/ValidationPanel'
import { usePoint } from './hooks/usePoint'

type Tab = 'orchard' | 'accuracy'

export default function App() {
  const [tab, setTab] = useState<Tab>('orchard')
  const [pin, setPin] = useState<[number, number]>([DEMO_PINS[0].lat, DEMO_PINS[0].lon])
  const [season, setSeason] = useState(2025)
  const [stations, setStations] = useState<Station[]>([])
  const { data, error, loading } = usePoint({ lat: pin[0], lon: pin[1], season })

  useEffect(() => {
    fetchStations()
      .then((r) => setStations(r.stations))
      .catch(() => setStations([]))
  }, [])

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Counting the Cold</h1>
          <p className="tagline">Your orchard's chill and heat, not a station's.</p>
        </div>
        <nav className="tabs">
          <button className={tab === 'orchard' ? 'active' : ''} onClick={() => setTab('orchard')}>
            Orchard
          </button>
          <button className={tab === 'accuracy' ? 'active' : ''} onClick={() => setTab('accuracy')}>
            How accurate is this?
          </button>
        </nav>
      </header>

      {tab === 'accuracy' ? (
        <ValidationPanel />
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
            <SettingsBar season={season} onSeason={setSeason} />
            {error && <div className="banner error">Couldn't load data: {error}</div>}
            {loading && !data && <div className="banner">Loading…</div>}
            {data && (
              <>
                {data.mock && <div className="banner">Showing synthetic mock data.</div>}
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
