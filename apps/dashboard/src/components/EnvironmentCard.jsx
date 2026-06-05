import { useState, useEffect } from 'react'
import * as api from '../api/environments'

const STATUS_COLORS = {
  creating: 'bg-yellow-100 text-yellow-700',
  running: 'bg-green-100 text-green-700',
  stopped: 'bg-gray-100 text-gray-700',
  error: 'bg-red-100 text-red-700',
  destroyed: 'bg-gray-200 text-gray-500',
}

const LIFECYCLE_COLORS = {
  provisioning: 'bg-amber-100 text-amber-800',
  bootstrapping: 'bg-yellow-100 text-yellow-800',
  building: 'bg-orange-100 text-orange-800',
  starting: 'bg-sky-100 text-sky-800',
  healthchecking: 'bg-cyan-100 text-cyan-800',
  validating: 'bg-violet-100 text-violet-800',
  running: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

const TYPE_COLORS = {
  main: 'bg-blue-100 text-blue-700',
  develop: 'bg-purple-100 text-purple-700',
  integration: 'bg-orange-100 text-orange-700',
  preview: 'bg-teal-100 text-teal-700',
  sandbox: 'bg-yellow-100 text-yellow-700',
  feature: 'bg-indigo-100 text-indigo-700',
  custom: 'bg-gray-100 text-gray-700',
}

function Badge({ label, colorClass }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {label}
    </span>
  )
}

function ActionButton({ label, onClick, disabled }) {
  const [busy, setBusy] = useState(false)

  async function handle() {
    setBusy(true)
    try { await onClick() } finally { setBusy(false) }
  }

  return (
    <button
      onClick={handle}
      disabled={disabled || busy}
      className="px-2 py-1 text-xs rounded bg-gray-100 hover:bg-gray-200 disabled:opacity-50"
    >
      {busy ? '…' : label}
    </button>
  )
}

function LogsModal({ envId, onClose }) {
  const [logs, setLogs] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getEnvironmentLogs(envId)
      .then(r => setLogs(r.data.logs || '(no logs)'))
      .catch(() => setLogs('(failed to fetch logs)'))
      .finally(() => setLoading(false))
  }, [envId])

  return (
    <div className="fixed inset-0 flex justify-end z-50">
      <div className="bg-black/40 flex-1" onClick={onClose} aria-hidden="true" />
      <div className="bg-gray-900 w-1/2 flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <span className="text-sm font-semibold text-gray-200">Logs — {envId}</span>
          <button className="text-gray-400 hover:text-white text-lg leading-none" onClick={onClose}>×</button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <p className="text-gray-500 text-xs">Loading…</p>
          ) : (
            <pre className="text-xs text-green-300 whitespace-pre-wrap">{logs}</pre>
          )}
        </div>
      </div>
    </div>
  )
}

function copyToClipboard(text) {
  navigator.clipboard?.writeText(text).catch(() => {})
}

export default function EnvironmentCard({ env, onAction }) {
  const [showLogs, setShowLogs] = useState(false)
  const [showDebug, setShowDebug] = useState(false)
  const [showRuntimePaths, setShowRuntimePaths] = useState(false)
  const [error, setError] = useState(null)

  async function handle(action) {
    setError(null)
    try {
      await action()
      await onAction()
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message)
    }
  }

  const statusColor = STATUS_COLORS[env.status] ?? 'bg-gray-100 text-gray-600'
  const lifecycleColor = LIFECYCLE_COLORS[env.lifecycle_phase] ?? 'bg-gray-100 text-gray-600'
  const typeColor = TYPE_COLORS[env.env_type] ?? 'bg-gray-100 text-gray-600'
  const isReady = env.status === 'running' && env.lifecycle_phase !== 'failed'
  const webUrl = isReady ? env.urls?.web : null
  const apiUrl = isReady ? env.urls?.api : null
  const hasPorts = env.ports && Object.keys(env.ports).length > 0

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 p-4 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-semibold text-gray-800">{env.env_name}</span>
          {env.env_type && <Badge label={env.env_type} colorClass={typeColor} />}
          <Badge label={env.status} colorClass={statusColor} />
          {env.lifecycle_phase && env.lifecycle_phase !== env.status && (
            <Badge label={env.lifecycle_phase} colorClass={lifecycleColor} />
          )}
          {env.deployment_mode && (
            <Badge
              label={env.deployment_mode === 'persistent' ? 'Persistent' : 'Deploy & Test'}
              colorClass="bg-gray-100 text-gray-600"
            />
          )}
        </div>
        <span className="text-xs text-gray-400 font-mono">{env.id}</span>
      </div>

      {/* Ref */}
      {env.ref && (
        <div className="text-xs text-gray-600">
          <span className="font-medium">{env.ref_type ?? 'ref'}:</span>{' '}
          <span className="font-mono">{env.ref}</span>
        </div>
      )}

      {/* Primary URLs */}
      {(webUrl || apiUrl) && (
        <div className="flex flex-col gap-1.5">
          {webUrl && (
            <div className="flex items-center gap-2">
              <a
                href={webUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-50 text-blue-700 rounded text-xs font-medium hover:bg-blue-100"
              >
                Open Web ↗
              </a>
              <span className="text-xs text-gray-500 font-mono truncate flex-1">{webUrl}</span>
              <button
                onClick={() => copyToClipboard(webUrl)}
                className="text-xs text-gray-400 hover:text-gray-600 px-1"
                title="Copy URL"
              >
                ⎘
              </button>
            </div>
          )}
          {apiUrl && (
            <div className="flex items-center gap-2">
              <a
                href={apiUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium hover:bg-indigo-100"
              >
                Open API ↗
              </a>
              <span className="text-xs text-gray-500 font-mono truncate flex-1">{apiUrl}</span>
              <button
                onClick={() => copyToClipboard(apiUrl)}
                className="text-xs text-gray-400 hover:text-gray-600 px-1"
                title="Copy URL"
              >
                ⎘
              </button>
            </div>
          )}
        </div>
      )}

      {/* Timestamps */}
      <div className="flex flex-wrap gap-2 text-xs text-gray-400">
        {env.deployed_at && <span>Deployed: {env.deployed_at}</span>}
        {env.stopped_at && <span>· Stopped: {env.stopped_at}</span>}
      </div>

      {env.lifecycle_error && (
        <p className="text-xs text-red-600">{env.lifecycle_error}</p>
      )}
      {error && <p className="text-xs text-red-600">{error}</p>}

      {/* Actions */}
      <div className="flex flex-wrap gap-2">
        <ActionButton label="Redeploy" onClick={() => handle(() => api.redeployEnvironment(env.id))} />
        <ActionButton label="Stop" onClick={() => handle(() => api.stopEnvironment(env.id))} />
        <ActionButton label="Refresh" onClick={() => handle(() => api.refreshEnvironment(env.id))} />
        <ActionButton label="Delete" onClick={() => handle(() => api.deleteEnvironment(env.id))} />
        <button
          onClick={() => setShowLogs(true)}
          className="px-2 py-1 text-xs rounded bg-gray-100 hover:bg-gray-200"
        >
          View Logs
        </button>
      </div>

      {/* Debug section — raw ports, collapsed by default */}
      {hasPorts && (
        <div>
          <button
            onClick={() => setShowDebug((v) => !v)}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            {showDebug ? '▾' : '▸'} Debug
          </button>
          {showDebug && (
            <div className="mt-1 bg-gray-50 rounded p-2 text-xs font-mono text-gray-500 space-y-0.5">
              {Object.entries(env.ports).map(([k, v]) => (
                <div key={k}>{k}: {v}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Runtime paths — collapsed by default */}
      {(env.project_root || env.sandbox_runtime_root || env.sandbox_dir || env.source_path) && (
        <div>
          <button
            onClick={() => setShowRuntimePaths((v) => !v)}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            {showRuntimePaths ? '▾' : '▸'} Runtime paths
          </button>
          {showRuntimePaths && (
            <div className="mt-1 bg-gray-50 rounded p-2 text-xs font-mono text-gray-500 space-y-0.5">
              {env.project_root && <div><span className="text-gray-600">project_root:</span> {env.project_root}</div>}
              {env.sandbox_runtime_root && <div><span className="text-gray-600">runtime_root:</span> {env.sandbox_runtime_root}</div>}
              {env.sandbox_dir && <div><span className="text-gray-600">sandbox_dir:</span> {env.sandbox_dir}</div>}
              {env.source_path && <div><span className="text-gray-600">source_path:</span> {env.source_path}</div>}
            </div>
          )}
        </div>
      )}

      {showLogs && <LogsModal envId={env.id} onClose={() => setShowLogs(false)} />}
    </div>
  )
}
