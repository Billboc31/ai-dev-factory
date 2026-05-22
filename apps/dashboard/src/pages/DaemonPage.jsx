import { useCallback, useState } from 'react'
import * as daemonApi from '../api/daemon'
import ActionButton from '../components/ActionButton'
import DaemonActivityFeed from '../components/DaemonActivityFeed'
import ErrorBanner from '../components/ErrorBanner'
import RuntimeStatusPanel from '../components/RuntimeStatusPanel'
import usePolling from '../hooks/usePolling'

function formatUptime(startedAt) {
  if (!startedAt) return null
  const seconds = Math.floor((Date.now() - new Date(startedAt)) / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
}

function WorkersList({ columns }) {
  if (!columns) return null
  const running = columns.find(c => c.id === 'running')
  if (!running || running.items.length === 0) return null
  return (
    <div className="mb-6">
      <h2 className="text-lg font-semibold mb-2">Workers</h2>
      <div className="space-y-2">
        {running.items.map(item => (
          <div key={item.ticket_id} className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-yellow-400 flex-shrink-0" aria-hidden="true" />
              <code className="font-mono font-semibold">{item.ticket_id}</code>
              {item.state && <span className="text-gray-500 text-xs">{item.state}</span>}
            </div>
            {item.branch && (
              <p className="text-xs text-gray-500 mt-1 font-mono truncate" title={item.branch}>{item.branch}</p>
            )}
            {item.worker_cwd && (
              <p className="text-xs text-gray-400 mt-0.5 font-mono truncate" title={item.worker_cwd}>
                cwd: {item.worker_cwd}
              </p>
            )}
            {item.worker_pid != null && (
              <p className="text-xs text-gray-400 mt-0.5 font-mono">pid: {item.worker_pid}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function CrashBanner({ status }) {
  if (!status?.exit_unexpected) return null
  return (
    <div role="alert" className="bg-red-50 border border-red-300 rounded p-4 mb-6">
      <p className="text-sm font-semibold text-red-900">Daemon crashed unexpectedly</p>
      {status.last_exit_code != null && (
        <p className="text-xs text-red-800 mt-1">
          Exit code: <code className="font-mono">{status.last_exit_code}</code>
        </p>
      )}
      {status.last_exit_time && (
        <p className="text-xs text-red-800">
          At: {new Date(status.last_exit_time).toLocaleTimeString()}
        </p>
      )}
      {status.restart_count > 0 && (
        <p className="text-xs text-red-800">Restarts: {status.restart_count}</p>
      )}
    </div>
  )
}

function HostCommandPanel({ command, onDismiss }) {
  const [copied, setCopied] = useState(false)
  if (!command) return null
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (_) {
      setCopied(false)
    }
  }
  return (
    <div
      role="alert"
      className="bg-yellow-50 border border-yellow-300 rounded p-4 mb-6"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-yellow-900">
            Daemon must be started on the host
          </p>
          <p className="text-xs text-yellow-800 mt-1">
            The API runs inside Docker. Copy the command below and run it in
            a host terminal, or configure{' '}
            <code className="font-mono">AI_DEV_FACTORY_HOST_DAEMON_COMMAND</code>{' '}
            so the API can delegate the launch.
          </p>
          <pre className="text-xs bg-yellow-100 p-2 rounded mt-2 overflow-x-auto whitespace-pre-wrap break-all font-mono">
            {command}
          </pre>
        </div>
        <div className="flex flex-col gap-1 flex-shrink-0">
          <button
            onClick={copy}
            className="px-2 py-1 text-xs bg-yellow-200 hover:bg-yellow-300 rounded font-medium"
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            onClick={onDismiss}
            className="px-2 py-1 text-xs text-yellow-700 hover:underline"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  )
}

export default function DaemonPage({ projectId }) {
  const [status, setStatus] = useState(null)
  const [columns, setColumns] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [hostCommand, setHostCommand] = useState(null)

  const fetchStatus = useCallback(() => {
    daemonApi.getDaemonStatus(projectId)
      .then(res => { setStatus(res.data); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [projectId])

  const fetchBoard = useCallback(() => {
    daemonApi.getBoardData(projectId)
      .then(res => setColumns(res.data.columns))
      .catch(() => {})
  }, [projectId])

  usePolling(fetchStatus, 5000, projectId)
  usePolling(fetchBoard, 5000, projectId)

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-4">Daemon</h1>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <CrashBanner status={status} />
      <HostCommandPanel command={hostCommand} onDismiss={() => setHostCommand(null)} />

      {loading && !status && <p className="text-gray-500">Loading…</p>}

      {status && (
        <div className="bg-white border border-gray-200 rounded p-4 mb-6 space-y-2">
          <div className="flex items-center gap-3">
            <span
              className={`w-3 h-3 rounded-full flex-shrink-0 ${status.running ? 'bg-green-400' : 'bg-gray-400'}`}
              aria-hidden="true"
            />
            <span className="font-semibold">{status.running ? 'Running' : 'Stopped'}</span>
            {status.restart_policy === 'restart-on-crash' && status.exit_unexpected && !status.running && (
              <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full font-medium">
                Restarting…
              </span>
            )}
          </div>
          {status.pid != null && (
            <p className="text-sm text-gray-600">PID: <code className="font-mono">{status.pid}</code></p>
          )}
          {status.started_at && (
            <p className="text-sm text-gray-600">
              Uptime: {formatUptime(status.started_at)}
            </p>
          )}
          {status.current_ticket && (
            <p className="text-sm text-gray-600">
              Current ticket: <code className="font-mono">{status.current_ticket}</code>
            </p>
          )}
          {status.last_heartbeat && (
            <p className="text-sm text-gray-400 text-xs">
              Last activity: {new Date(status.last_heartbeat).toLocaleTimeString()}
            </p>
          )}
        </div>
      )}

      <div className="flex gap-2 mb-8">
        <ActionButton
          label="Start"
          action={() => daemonApi.startDaemon(projectId)}
          onSuccess={fetchStatus}
          onResult={(data) => setHostCommand(data?.host_command || null)}
        />
        <ActionButton label="Stop" action={() => daemonApi.stopDaemon(projectId)} variant="danger" onSuccess={fetchStatus} />
        <ActionButton label="Restart" action={() => daemonApi.restartDaemon(projectId)} variant="secondary" onSuccess={fetchStatus} />
        <ActionButton label="Sync Main" action={() => daemonApi.syncMain(projectId)} variant="secondary" onSuccess={fetchStatus} />
      </div>

      <WorkersList columns={columns} />

      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Runtime Status</h2>
        <div className="bg-white border border-gray-200 rounded p-4">
          <RuntimeStatusPanel projectId={projectId} />
        </div>
      </div>

      <div>
        <h2 className="text-lg font-semibold mb-2">Activity Feed</h2>
        <DaemonActivityFeed projectId={projectId} />
      </div>
    </div>
  )
}
