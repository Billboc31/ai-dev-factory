import { useState } from 'react'
import { getRuntimeStatus } from '../api/daemon'
import usePolling from '../hooks/usePolling'

function WorkersSection({ workers }) {
  if (!workers || workers.length === 0) {
    return <p className="text-sm text-gray-400">No active workers</p>
  }
  return (
    <ul className="space-y-1">
      {workers.map(w => (
        <li key={w.ticket_id} className="flex items-center gap-2 text-sm">
          <span className="w-2 h-2 rounded-full bg-yellow-400 flex-shrink-0" aria-hidden="true" />
          <code className="font-mono font-semibold">{w.ticket_id}</code>
          {w.state && <span className="text-gray-500 text-xs">{w.state}</span>}
          {w.pid != null && <span className="text-gray-400 text-xs">pid:{w.pid}</span>}
        </li>
      ))}
    </ul>
  )
}

function RetrySection({ retryBlocked }) {
  if (!retryBlocked || retryBlocked.length === 0) {
    return <p className="text-sm text-gray-400">No blocked tickets</p>
  }
  return (
    <ul className="space-y-1">
      {retryBlocked.map(t => (
        <li key={t.ticket_id} className="text-sm">
          <code className="font-mono font-semibold">{t.ticket_id}</code>
          {t.retry_count > 0 && (
            <span className="text-orange-600 ml-2">×{t.retry_count}</span>
          )}
          {t.cooldown_until && (
            <span className="text-xs text-gray-500 ml-2">
              cooldown until {new Date(t.cooldown_until).toLocaleTimeString()}
            </span>
          )}
          {t.failure_class && (
            <span className="text-xs text-gray-400 ml-2">{t.failure_class}</span>
          )}
        </li>
      ))}
    </ul>
  )
}

function QueueSection({ intakeQueue }) {
  if (!intakeQueue || intakeQueue.length === 0) {
    return <p className="text-sm text-gray-400">Queue empty</p>
  }
  return (
    <ul className="space-y-1">
      {intakeQueue.map((entry, i) => (
        <li key={entry.issue_number ?? i} className="text-sm">
          {entry.issue_number != null && (
            <span className="text-gray-500 mr-1">#{entry.issue_number}</span>
          )}
          <span>{entry.title}</span>
        </li>
      ))}
    </ul>
  )
}

export default function RuntimeStatusPanel() {
  const [runtimeStatus, setRuntimeStatus] = useState(null)
  const [error, setError] = useState(null)

  usePolling(() => {
    getRuntimeStatus()
      .then(res => { setRuntimeStatus(res.data); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, 5000)

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-700" role="alert">
        Runtime status unavailable: {error}
      </div>
    )
  }

  if (!runtimeStatus) {
    return <p className="text-gray-400 text-sm">Loading runtime status…</p>
  }

  return (
    <div className="space-y-4">
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-1">Active Workers</h3>
        <WorkersSection workers={runtimeStatus.workers} />
      </section>
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-1">Retry / Cooldown</h3>
        <RetrySection retryBlocked={runtimeStatus.retry_blocked} />
      </section>
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-1">Intake Queue</h3>
        <QueueSection intakeQueue={runtimeStatus.intake_queue} />
      </section>
      {runtimeStatus.last_error && (
        <section>
          <h3 className="text-sm font-semibold text-red-700 mb-1">Last Error</h3>
          <p className="text-xs font-mono text-red-600 bg-red-50 rounded p-2 overflow-x-auto">
            {runtimeStatus.last_error}
          </p>
        </section>
      )}
      {runtimeStatus.last_action && (
        <p className="text-xs text-gray-400">
          Last activity: {new Date(runtimeStatus.last_action).toLocaleTimeString()}
        </p>
      )}
    </div>
  )
}
