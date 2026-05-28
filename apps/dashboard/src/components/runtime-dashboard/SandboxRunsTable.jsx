import { useState } from 'react'
import * as api from '../../api/runtimeDashboard'
import ConfirmDialog from './ConfirmDialog'

const STATUS_COLORS = {
  running:   'bg-green-100 text-green-700',
  creating:  'bg-yellow-100 text-yellow-700',
  idle:      'bg-yellow-100 text-yellow-700',
  active:    'bg-green-100 text-green-700',
  success:   'bg-blue-100 text-blue-700',
  completed: 'bg-blue-100 text-blue-700',
  stopped:   'bg-gray-100 text-gray-700',
  failed:    'bg-red-100 text-red-700',
  error:     'bg-red-100 text-red-700',
  destroyed: 'bg-gray-200 text-gray-500',
}

const ACTIVE_STATUSES = new Set(['running', 'creating', 'active'])

function StatusBadge({ status }) {
  const colorClass = STATUS_COLORS[status] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {ACTIVE_STATUSES.has(status) && <span className="animate-spin inline-block">↻</span>}
      {status}
    </span>
  )
}

function Chip({ label, value, color = 'gray' }) {
  const colors = {
    green:  'bg-green-100 text-green-700',
    red:    'bg-red-100 text-red-700',
    gray:   'bg-gray-100 text-gray-600',
    yellow: 'bg-yellow-100 text-yellow-700',
    blue:   'bg-blue-100 text-blue-700',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colors[color] || colors.gray}`}>
      {label && <span className="opacity-60">{label}:</span>}
      {value}
    </span>
  )
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }
  return (
    <button
      onClick={handleCopy}
      className="px-1.5 py-0.5 text-xs border border-gray-300 rounded hover:bg-gray-50 text-gray-500"
      title="Copy URL"
    >
      {copied ? '✓' : '⎘'}
    </button>
  )
}

function EnvironmentCard({ run, onOpenLogs, onStopRequest, onDeleteRequest, deleting }) {
  const [showPorts, setShowPorts] = useState(false)
  const isActive = ACTIVE_STATUSES.has(run.status)
  const urls = run.urls || {}
  const ports = run.ports || {}
  const hasPorts = Object.keys(ports).length > 0

  const proxyColor = run.proxy_ready === true ? 'green' : run.proxy_ready === false ? 'red' : 'gray'
  const healthColor =
    run.healthcheck_status === 'ok' || run.healthcheck_status === 'pass' ? 'green'
    : run.healthcheck_status === 'fail' || run.healthcheck_status === 'failed' ? 'red'
    : 'gray'
  const smokeColor =
    run.smoke_status === 'ok' || run.smoke_status === 'pass' ? 'green'
    : run.smoke_status === 'fail' || run.smoke_status === 'failed' ? 'red'
    : 'gray'

  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3 bg-white">
      {/* header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-sm font-semibold text-gray-800">{run.id}</span>
          {run.project_id && (
            <span className="text-xs text-gray-500">{run.project_id}</span>
          )}
          {run.ref && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-mono bg-purple-50 text-purple-700 border border-purple-200">
              {run.ref}
            </span>
          )}
        </div>
        <StatusBadge status={run.status} />
      </div>

      {/* failing step banner */}
      {run.failing_step && (
        <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          <span className="font-medium">Failing step:</span>
          <span>{run.failing_step}</span>
          <button
            className="ml-auto underline hover:no-underline"
            onClick={() => onOpenLogs?.(run.id)}
          >
            View logs
          </button>
        </div>
      )}

      {/* primary URLs */}
      {Object.keys(urls).length > 0 ? (
        <div className="space-y-1.5">
          {Object.entries(urls).map(([name, url]) => (
            <div key={name} className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-8 shrink-0 uppercase font-medium">{name}</span>
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 text-sm font-mono text-blue-600 hover:underline truncate"
              >
                {url}
              </a>
              <CopyButton text={url} />
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-1.5 py-0.5 text-xs border border-blue-300 rounded text-blue-600 hover:bg-blue-50"
                title="Open in new tab"
              >
                ↗
              </a>
            </div>
          ))}
        </div>
      ) : (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-500">
          no proxy
        </span>
      )}

      {/* ports collapsible */}
      {hasPorts && (
        <div>
          <button
            className="text-xs text-gray-400 hover:text-gray-600 underline"
            onClick={() => setShowPorts(p => !p)}
          >
            {showPorts ? 'Hide' : 'Show'} debug ports
          </button>
          {showPorts && (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {Object.entries(ports).map(([k, v]) => (
                <span key={k} className="font-mono text-xs bg-gray-50 border border-gray-200 rounded px-2 py-0.5 text-gray-600">
                  {k}: localhost:{v}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* status chips */}
      {(run.proxy_ready !== null && run.proxy_ready !== undefined || run.healthcheck_status || run.smoke_status) && (
        <div className="flex flex-wrap gap-1.5">
          {run.proxy_ready !== null && run.proxy_ready !== undefined && (
            <Chip label="proxy" value={run.proxy_ready ? 'ready' : 'not ready'} color={proxyColor} />
          )}
          {run.healthcheck_status && (
            <Chip label="health" value={run.healthcheck_status} color={healthColor} />
          )}
          {run.smoke_status && (
            <Chip label="smoke" value={run.smoke_status} color={smokeColor} />
          )}
        </div>
      )}

      {/* info row */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-500">
        {run.compose_project && (
          <div>
            <span className="font-medium">compose:</span>{' '}
            <span className="font-mono">{run.compose_project}</span>
          </div>
        )}
        {run.runtime_root && (
          <div className="truncate">
            <span className="font-medium">runtime:</span>{' '}
            <span className="font-mono">{run.runtime_root}</span>
          </div>
        )}
        {run.worktree_path && (
          <div className="truncate col-span-2">
            <span className="font-medium">worktree:</span>{' '}
            <span className="font-mono">{run.worktree_path}</span>
          </div>
        )}
        {run.created_at && (
          <div>
            <span className="font-medium">created:</span> {run.created_at}
          </div>
        )}
        {run.started_at && (
          <div>
            <span className="font-medium">started:</span> {run.started_at}
          </div>
        )}
        {run.last_checked_at && (
          <div>
            <span className="font-medium">checked:</span> {run.last_checked_at}
          </div>
        )}
      </div>

      {/* actions */}
      <div className="flex gap-1.5 pt-1 border-t border-gray-100">
        <button
          className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 text-gray-600"
          onClick={() => onOpenLogs?.(run.id)}
        >
          View Logs
        </button>
        <button
          className="px-2 py-1 text-xs border border-orange-300 rounded text-orange-600 hover:bg-orange-50 disabled:opacity-40 disabled:cursor-not-allowed"
          onClick={() => onStopRequest?.(run.id)}
          disabled={!isActive || deleting === run.id}
        >
          Stop
        </button>
        <button
          className="px-2 py-1 text-xs border border-red-300 rounded text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed"
          onClick={() => onDeleteRequest?.(run.id)}
          disabled={isActive || deleting === run.id}
        >
          {deleting === run.id ? '…' : 'Delete'}
        </button>
      </div>
    </div>
  )
}

export default function SandboxRunsTable({ runs, onOpenLogs, onDeleted }) {
  const [confirmId, setConfirmId] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [deleteError, setDeleteError] = useState(null)

  const handleStopRequest = (id) => {
    setConfirmId(id)
    setConfirmAction('stop')
  }

  const handleDeleteRequest = (id) => {
    setConfirmId(id)
    setConfirmAction('delete')
  }

  const handleConfirm = async () => {
    const id = confirmId
    const action = confirmAction
    setConfirmId(null)
    setConfirmAction(null)
    setDeleting(id)
    setDeleteError(null)
    try {
      if (action === 'stop') {
        await api.stopSandboxRun(id)
      } else {
        await api.deleteSandboxRun(id)
      }
      onDeleted?.()
    } catch (err) {
      setDeleteError(err.response?.data?.detail || err.message)
    } finally {
      setDeleting(null)
    }
  }

  if (runs.length === 0) {
    return <p className="text-sm text-gray-400">No running environments found.</p>
  }

  return (
    <>
      {deleteError && (
        <p className="text-xs text-red-600 mb-2">{deleteError}</p>
      )}
      <div className="space-y-4">
        {runs.map(run => (
          <EnvironmentCard
            key={run.id}
            run={run}
            onOpenLogs={onOpenLogs}
            onStopRequest={handleStopRequest}
            onDeleteRequest={handleDeleteRequest}
            deleting={deleting}
          />
        ))}
      </div>

      {confirmId && (
        <ConfirmDialog
          message={
            confirmAction === 'stop'
              ? `Stop sandbox "${confirmId}"?`
              : `Delete sandbox run "${confirmId}"? This cannot be undone.`
          }
          onConfirm={handleConfirm}
          onCancel={() => { setConfirmId(null); setConfirmAction(null) }}
        />
      )}
    </>
  )
}
