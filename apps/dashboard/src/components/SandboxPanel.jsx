import { useCallback, useEffect, useState } from 'react'
import * as sandboxApi from '../api/sandbox'
import ActionButton from './ActionButton'
import ErrorBanner from './ErrorBanner'
import usePolling from '../hooks/usePolling'

const STATUS_COLORS = {
  creating: 'bg-yellow-100 text-yellow-700',
  running: 'bg-green-100 text-green-700',
  stopped: 'bg-gray-100 text-gray-700',
  error: 'bg-red-100 text-red-700',
  destroyed: 'bg-gray-200 text-gray-500',
}

function StatusBadge({ status }) {
  const colorClass = STATUS_COLORS[status] || STATUS_COLORS.stopped
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {status === 'running' && <span className="animate-spin inline-block">↻</span>}
      {status}
    </span>
  )
}

function PortsTable({ ports }) {
  const entries = Object.entries(ports)
  if (entries.length === 0) return null
  return (
    <table className="text-xs text-gray-600 mt-1">
      <tbody>
        {entries.map(([name, port]) => (
          <tr key={name}>
            <td className="pr-3 font-mono text-gray-400">{name}</td>
            <td className="font-mono">{port}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function LogsModal({ sandboxId, onClose }) {
  const [logs, setLogs] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    sandboxApi.getSandboxLogs(sandboxId)
      .then(res => setLogs(res.data.logs))
      .catch(err => setLogs(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [sandboxId])

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-2/3 max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
          <span className="text-sm font-semibold text-gray-700">Logs — {sandboxId}</span>
          <button
            className="text-gray-400 hover:text-gray-600 text-lg leading-none"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 bg-gray-900 rounded-b">
          {loading ? (
            <p className="text-gray-400 text-xs">Loading…</p>
          ) : logs ? (
            <pre className="text-xs text-green-300 whitespace-pre-wrap">{logs}</pre>
          ) : (
            <p className="text-gray-400 text-xs">No logs available.</p>
          )}
        </div>
      </div>
    </div>
  )
}

function SandboxRow({ sandbox, onRefresh }) {
  const [logsOpen, setLogsOpen] = useState(false)
  const isRunning = sandbox.status === 'running'

  return (
    <div className="bg-white border border-gray-200 rounded p-4 space-y-2">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <StatusBadge status={sandbox.status} />
          <span className="text-sm font-mono text-gray-700">{sandbox.id}</span>
          <span className="text-xs text-gray-400">ticket: {sandbox.ticket_id}</span>
          {sandbox.job_type && (
            <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded font-mono">
              {sandbox.job_type}
            </span>
          )}
        </div>
        <span className="text-xs text-gray-400">{sandbox.created_at}</span>
      </div>
      <PortsTable ports={sandbox.ports} />
      {sandbox.worktree_path && (
        <p className="text-xs text-gray-400 font-mono truncate">
          worktree: {sandbox.worktree_path}
        </p>
      )}
      <div className="flex gap-2 flex-wrap pt-1">
        <ActionButton
          label="Start"
          action={() => sandboxApi.startSandbox(sandbox.id)}
          disabled={isRunning}
          onSuccess={onRefresh}
          variant="primary"
        />
        <ActionButton
          label="Stop"
          action={() => sandboxApi.stopSandbox(sandbox.id)}
          disabled={!isRunning}
          onSuccess={onRefresh}
          variant="secondary"
        />
        <ActionButton
          label="Destroy"
          action={() => sandboxApi.destroySandbox(sandbox.id)}
          onSuccess={onRefresh}
          variant="danger"
        />
        <button
          className="px-3 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 text-gray-600"
          onClick={() => setLogsOpen(true)}
        >
          Logs
        </button>
      </div>
      {logsOpen && <LogsModal sandboxId={sandbox.id} onClose={() => setLogsOpen(false)} />}
    </div>
  )
}

export default function SandboxPanel() {
  const [sandboxes, setSandboxes] = useState([])
  const [ticketId, setTicketId] = useState('')
  const [projectRoot, setProjectRoot] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState(null)

  const refresh = useCallback(() => {
    sandboxApi.listSandboxes()
      .then(res => { setSandboxes(res.data); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [])

  usePolling(refresh, 5000)

  const handleCreate = async () => {
    if (!ticketId.trim() || !projectRoot.trim()) return
    setCreating(true)
    setError(null)
    try {
      await sandboxApi.createSandbox(ticketId.trim(), projectRoot.trim())
      setTicketId('')
      setProjectRoot('')
      refresh()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setCreating(false)
    }
  }

  const handleCleanup = async () => {
    setError(null)
    try {
      await sandboxApi.cleanupSandboxes(7)
      refresh()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  return (
    <div className="max-w-2xl">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Sandboxes</h1>
        <button
          className="text-xs text-gray-500 hover:text-gray-700 border border-gray-300 rounded px-2 py-1"
          onClick={handleCleanup}
        >
          Cleanup old (&gt;7d)
        </button>
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="bg-white border border-gray-200 rounded p-4 mb-6 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Create sandbox</h2>
        <div className="flex gap-2 flex-wrap">
          <input
            type="text"
            placeholder="Ticket ID (e.g. T133)"
            value={ticketId}
            onChange={e => setTicketId(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-sm flex-1 min-w-32"
          />
          <input
            type="text"
            placeholder="Project root path"
            value={projectRoot}
            onChange={e => setProjectRoot(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-sm flex-1 min-w-48"
          />
          <button
            className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            onClick={handleCreate}
            disabled={creating || !ticketId.trim() || !projectRoot.trim()}
          >
            {creating ? 'Creating…' : 'Create'}
          </button>
        </div>
      </div>

      {sandboxes.length === 0 ? (
        <p className="text-sm text-gray-400">No sandboxes.</p>
      ) : (
        <div className="space-y-3">
          {sandboxes.map(s => (
            <SandboxRow key={s.id} sandbox={s} onRefresh={refresh} />
          ))}
        </div>
      )}
    </div>
  )
}
