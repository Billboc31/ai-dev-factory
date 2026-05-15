import { useEffect, useState, useCallback } from 'react'
import * as daemonApi from '../api/daemon'
import ActionButton from '../components/ActionButton'
import ErrorBanner from '../components/ErrorBanner'

function formatUptime(startedAt) {
  if (!startedAt) return null
  const seconds = Math.floor((Date.now() - new Date(startedAt)) / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
}

export default function DaemonPage() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStatus = useCallback(() => {
    daemonApi.getDaemonStatus()
      .then(res => { setStatus(res.data); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  return (
    <div className="max-w-md">
      <h1 className="text-2xl font-bold mb-4">Daemon</h1>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      {loading && !status && <p className="text-gray-500">Loading…</p>}

      {status && (
        <div className="bg-white border border-gray-200 rounded p-4 mb-6 space-y-2">
          <div className="flex items-center gap-3">
            <span
              className={`w-3 h-3 rounded-full flex-shrink-0 ${status.running ? 'bg-green-400' : 'bg-gray-400'}`}
              aria-hidden="true"
            />
            <span className="font-semibold">{status.running ? 'Running' : 'Stopped'}</span>
          </div>
          {status.pid != null && (
            <p className="text-sm text-gray-600">PID: <code className="font-mono">{status.pid}</code></p>
          )}
          {status.started_at && (
            <p className="text-sm text-gray-600">
              Uptime: {formatUptime(status.started_at)}
            </p>
          )}
        </div>
      )}

      <div className="flex gap-2">
        <ActionButton label="Start" action={daemonApi.startDaemon} onSuccess={fetchStatus} />
        <ActionButton label="Stop" action={daemonApi.stopDaemon} variant="danger" onSuccess={fetchStatus} />
        <ActionButton label="Restart" action={daemonApi.restartDaemon} variant="secondary" onSuccess={fetchStatus} />
      </div>
    </div>
  )
}
