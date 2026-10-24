import { ApiError } from '../api/client'
import { formatDate } from '../geo'
import { useSingleOpen } from '../hooks/useSingleOpen'
import { METRICS } from '../metrics'
import { ClockIcon, OfflineIcon, WarnIcon } from './icons'
import InfoButton from './InfoButton'
import { metricCopy } from './metricInfo'

// Data older than its normal refresh: served from an expired cache entry (quality.stale). The contract has no
// timestamp for it, so the wording is generic.
export function StaleBanner({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div className="banner warn" role="status">
      <ClockIcon size={20} />
      <span className="banner-text">
        <strong>Showing saved data.</strong> The live feed is late, so numbers may be a day behind.
      </span>
      <button type="button" className="chip" onClick={onRefresh}>
        Refresh
      </button>
    </div>
  )
}

// No signal: the numbers on screen are the last ones saved on this phone.
export function OfflineBanner({ asOf, onRetry }: { asOf: string; onRetry: () => void }) {
  return (
    <div className="banner warn" role="status">
      <OfflineIcon />
      <span className="banner-text">
        <strong>You're offline.</strong> Showing the saved numbers, as of {formatDate(asOf)}.
      </span>
      <button type="button" className="chip" onClick={onRetry}>
        Try again
      </button>
    </div>
  )
}

interface ErrorProps {
  error: Error
  hasLast: boolean // an earlier response is still available
  onRetry: () => void
  onShowLast: () => void
}

export function ErrorCard({ error, hasLast, onRetry, onShowLast }: ErrorProps) {
  const status = error instanceof ApiError ? error.status : undefined
  const detail = error instanceof ApiError ? error.detail : undefined
  return (
    <section className="card error-card" role="alert">
      <WarnIcon size={32} />
      <div>
        <h2>We couldn't get your numbers</h2>
        <p>
          The data service didn't answer. Your pin is saved, and nothing is lost. Try again
          {hasLast ? ', or open the last numbers we have for this spot.' : '.'}
        </p>
        {detail && <p className="error-detail">{detail}</p>}
        <div className="error-actions">
          <button type="button" className="chip primary" onClick={onRetry}>
            Try again
          </button>
          {hasLast && (
            <button type="button" className="chip" onClick={onShowLast}>
              Show last saved numbers
            </button>
          )}
        </div>
        <span className="lbl error-code">{status ? `Error ${status}` : 'No answer from the data service'}</span>
      </div>
    </section>
  )
}

// Shown after "Show last saved numbers": the old response is on screen, and says so.
export function LastNumbersBanner({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="banner warn" role="status">
      <WarnIcon size={20} />
      <span className="banner-text">
        <strong>Showing the last numbers we loaded.</strong> The data service isn't answering right now.
      </span>
      <button type="button" className="chip" onClick={onRetry}>
        Try again
      </button>
    </div>
  )
}

// First load, nothing to show yet: shimmer blocks shaped like the cards and the chart. No spinners.
export function LoadingSkeleton({ lat, lon }: { lat: number; lon: number }) {
  const heights = [43, 52, 62, 36, 49, 58, 66, 38, 55, 48, 60]
  const { openId, toggle, close } = useSingleOpen()
  return (
    <div className="skeleton-page" aria-busy="true">
      <div className="cards">
        {METRICS.map((m) => (
          <div className={`card skel-card ${m.accent}`} key={m.metric}>
            <div className="skel-head">
              <span className="lbl">{m.label}</span>
              <InfoButton
                title={m.label}
                text={metricCopy(m.metric)}
                accent={m.accent}
                open={openId === m.metric}
                onToggle={() => toggle(m.metric)}
                onClose={close}
              />
            </div>
            <div className="skeleton" aria-hidden="true" style={{ width: '70%', height: 48, margin: '14px 0' }} />
            <div className="skeleton" aria-hidden="true" style={{ width: '100%', height: 8 }} />
            <div className="skeleton" aria-hidden="true" style={{ width: '55%', height: 8, marginTop: 10 }} />
          </div>
        ))}
      </div>
      <div className="card skel-chart" aria-hidden="true">
        <div className="skeleton" style={{ width: '30%', height: 12 }} />
        <div className="skel-bars">
          {heights.map((h, i) => (
            <div className="skeleton" key={i} style={{ height: `${h}%` }} />
          ))}
        </div>
      </div>
      <p className="skel-status" role="status">
        Pulling hourly data for {lat}, {lon} …
      </p>
    </div>
  )
}
