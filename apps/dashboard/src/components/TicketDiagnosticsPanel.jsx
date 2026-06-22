import { useCallback, useEffect, useState } from 'react'
import * as api from '../api/tickets'

const SEVERITY_COLORS = {
  info:    'bg-blue-100 text-blue-800',
  warning: 'bg-amber-100 text-amber-800',
  error:   'bg-red-100 text-red-800',
}

const CHECK_STATUS_COLORS = {
  passed:  'bg-green-100 text-green-800',
  failed:  'bg-red-100 text-red-800',
  unknown: 'bg-gray-100 text-gray-600',
  skipped: 'bg-gray-100 text-gray-600',
}

const RISK_COLORS = {
  low:         'bg-green-100 text-green-800',
  medium:      'bg-amber-100 text-amber-800',
  high:        'bg-orange-100 text-orange-800',
  destructive: 'bg-red-100 text-red-800',
}

function StuckBadge({ isStuck }) {
  const color = isStuck ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
  const label = isStuck ? 'STUCK' : 'HEALTHY'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold tracking-wide ${color}`}>
      {label}
    </span>
  )
}

function SeverityBadge({ severity }) {
  if (!severity) return null
  const color = SEVERITY_COLORS[severity] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${color}`}>
      {severity}
    </span>
  )
}

function CheckStatusPill({ status }) {
  const color = CHECK_STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {status}
    </span>
  )
}

function RiskPill({ risk }) {
  const color = RISK_COLORS[risk] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium uppercase ${color}`}>
      {risk}
    </span>
  )
}

export default function TicketDiagnosticsPanel({ ticketId, projectId }) {
  const [diagnostics, setDiagnostics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const fetchDiagnostics = useCallback(() => {
    return api.getTicketDiagnostics(ticketId, projectId)
      .then(res => {
        setDiagnostics(res.data)
        setErr(null)
        return res.data
      })
      .catch(e => {
        if (e.response?.status === 404) {
          setDiagnostics(null)
          return null
        }
        setErr(e.response?.data?.detail || e.message)
        return null
      })
  }, [ticketId, projectId])

  useEffect(() => {
    setLoading(true)
    setDiagnostics(null)
    setErr(null)
    fetchDiagnostics().finally(() => setLoading(false))
  }, [ticketId, projectId, fetchDiagnostics])

  const runDiagnostics = () => {
    setBusy(true)
    setErr(null)
    api.runTicketDiagnostics(ticketId, projectId)
      .then(res => {
        setDiagnostics(res.data)
        return fetchDiagnostics()
      })
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setBusy(false))
  }

  const checks = diagnostics?.checks ?? []
  const actions = diagnostics?.recommended_actions ?? []

  return (
    <div className="bg-white border border-gray-200 rounded p-4 space-y-4 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-700">Ticket Diagnostics</h2>
          {diagnostics && <StuckBadge isStuck={!!diagnostics.is_stuck} />}
          {diagnostics?.severity && <SeverityBadge severity={diagnostics.severity} />}
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
            Read-only — recommendations only
          </span>
        </div>
        <button
          onClick={runDiagnostics}
          disabled={busy}
          className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {busy ? 'Running…' : (diagnostics ? 'Re-run diagnostics' : 'Run diagnostics')}
        </button>
      </div>

      {err && <p className="text-red-600 text-xs">{err}</p>}

      {loading && <p className="text-gray-400 text-sm">Loading…</p>}

      {!loading && !diagnostics && !err && (
        <p className="text-gray-500 text-sm">
          No diagnostic yet. Click <em>Run diagnostics</em> to analyse this ticket.
        </p>
      )}

      {diagnostics && (
        <>
          {diagnostics.summary && (
            <p className="text-sm text-gray-800">{diagnostics.summary}</p>
          )}

          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-x-6 gap-y-2 text-xs">
            <div>
              <dt className="text-gray-500 font-medium">Current state</dt>
              <dd className="font-mono text-gray-800">{diagnostics.current_state ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-gray-500 font-medium">Last known step</dt>
              <dd className="font-mono text-gray-800">{diagnostics.last_known_step ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-gray-500 font-medium">Last error</dt>
              <dd className="font-mono text-gray-800 break-all">{diagnostics.last_error ?? '—'}</dd>
            </div>
          </dl>

          {checks.length > 0 && (
            <div className="border border-gray-200 rounded p-3">
              <p className="text-xs font-medium text-gray-700 mb-2">Checks</p>
              <ul className="space-y-1">
                {checks.map((c, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs">
                    <CheckStatusPill status={c.status} />
                    <div className="flex-1">
                      <span className="font-mono text-gray-700">{c.key}</span>
                      <span className="text-gray-600"> — {c.message}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {actions.length > 0 && (
            <div className="border border-gray-200 rounded p-3">
              <p className="text-xs font-medium text-gray-700 mb-2">Recommended actions</p>
              <ul className="space-y-2">
                {actions.map((a, idx) => (
                  <li key={idx} className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled
                        title="Action not wired yet"
                        className="px-2 py-1 text-xs bg-gray-200 text-gray-500 rounded cursor-not-allowed"
                      >
                        {a.label}
                      </button>
                      <RiskPill risk={a.risk} />
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
                        Action not wired yet
                      </span>
                    </div>
                    {a.reason && (
                      <p className="text-xs text-gray-600 ml-1">{a.reason}</p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {diagnostics.generated_at && (
            <p className="text-xs text-gray-400">
              Generated: {new Date(diagnostics.generated_at).toLocaleString()}
            </p>
          )}
        </>
      )}
    </div>
  )
}
