import { useCallback, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getRuntimeStatus } from '../api/daemon'
import DaemonActivityFeed from '../components/DaemonActivityFeed'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (_) {}
  }
  return (
    <button
      onClick={copy}
      className="ml-2 text-xs text-gray-400 hover:text-gray-700 font-mono"
      title="Copy path"
    >
      {copied ? '✓' : 'copy'}
    </button>
  )
}

function PathRow({ label, value }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-2 py-2 border-b border-gray-100 last:border-0">
      <span className="text-xs text-gray-500 w-32 shrink-0">{label}</span>
      <div className="flex items-center min-w-0">
        <span className="text-xs font-mono text-gray-700 truncate" title={value}>{value}</span>
        <CopyButton text={value} />
      </div>
    </div>
  )
}

function RuntimeStatusTab({ projectId }) {
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)

  const fetch = useCallback(() => {
    getRuntimeStatus(projectId)
      .then(res => { setStatus(res.data); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [projectId])

  usePolling(fetch, 10000, projectId)

  if (error) return <ErrorBanner message={error} onClose={() => setError(null)} />
  if (!status) return <p className="text-gray-400 text-sm">Loading runtime status…</p>

  return (
    <div className="space-y-6">
      <div className="bg-white border border-gray-200 rounded p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Runtime Paths</h3>
        <PathRow label="Runtime root" value={status.runtime_root} />
        <PathRow label="Daemon log" value={status.daemon_log} />
        <PathRow label="Supervisor log" value={status.supervisor_log} />
        <PathRow label="Socket" value={status.socket_path} />
        <PathRow label="PID file" value={status.pid_file} />
      </div>

      <div className="bg-white border border-gray-200 rounded p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Process State</h3>
        <div className="space-y-1">
          {status.pid != null && (
            <p className="text-sm text-gray-600">
              PID: <code className="font-mono">{status.pid}</code>
            </p>
          )}
          {status.last_action && (
            <p className="text-sm text-gray-600">
              Last activity: {new Date(status.last_action).toLocaleString()}
            </p>
          )}
          {status.last_error && (
            <div className="mt-2">
              <p className="text-xs font-semibold text-red-700 mb-1">Last error</p>
              <pre className="text-xs font-mono text-red-800 bg-red-50 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                {status.last_error}
              </pre>
            </div>
          )}
        </div>
      </div>

      {status.workers && status.workers.length > 0 && (
        <div className="bg-white border border-gray-200 rounded p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Active Workers</h3>
          <ul className="space-y-1">
            {status.workers.map(w => (
              <li key={w.ticket_id} className="flex items-center gap-2 text-sm">
                <span className="w-2 h-2 rounded-full bg-yellow-400 shrink-0" aria-hidden="true" />
                <code className="font-mono font-semibold">{w.ticket_id}</code>
                {w.state && <span className="text-gray-500 text-xs">{w.state}</span>}
                {w.pid != null && <span className="text-gray-400 text-xs">pid:{w.pid}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function ProjectLogsPage() {
  const { projectId } = useParams()
  const [tab, setTab] = useState('daemon')

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-2xl font-bold">Logs</h1>

      <div className="flex border-b border-gray-200">
        {[
          { id: 'daemon', label: 'Daemon Logs' },
          { id: 'runtime', label: 'Runtime Status' },
        ].map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              tab === id
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'daemon' && <DaemonActivityFeed projectId={projectId} lines={100} />}
      {tab === 'runtime' && <RuntimeStatusTab projectId={projectId} />}
    </div>
  )
}
