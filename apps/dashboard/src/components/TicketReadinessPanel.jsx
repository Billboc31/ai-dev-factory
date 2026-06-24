import { useCallback, useEffect, useState } from 'react'
import * as api from '../api/tickets'
import usePolling from '../hooks/usePolling'

const ACTIVE_STATUSES = new Set(['queued', 'running'])
const POLL_INTERVAL = 4000

const STATUS_LABELS = {
  not_started:     'NOT STARTED',
  queued:          'QUEUED',
  running:         'RUNNING',
  ready_candidate: 'READY CANDIDATE',
  blocked:         'BLOCKED',
  failed:          'FAILED',
}

const STATUS_COLORS = {
  not_started:     'bg-gray-100 text-gray-600',
  queued:          'bg-yellow-100 text-yellow-800',
  running:         'bg-blue-100 text-blue-800 animate-pulse',
  ready_candidate: 'bg-green-100 text-green-800',
  blocked:         'bg-red-100 text-red-800',
  failed:          'bg-red-100 text-red-800',
}

const SUBCHECK_COLORS = {
  passed:   'bg-green-100 text-green-800',
  failed:   'bg-red-100 text-red-800',
  advisory: 'bg-amber-100 text-amber-800',
  unknown:  'bg-gray-100 text-gray-600',
  fresh:    'bg-green-100 text-green-800',
  stale:    'bg-orange-100 text-orange-800',
}

function StatusBadge({ status }) {
  const label = STATUS_LABELS[status] ?? status
  const color = STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold tracking-wide ${color}`}>
      {label}
    </span>
  )
}

function SubCheckBadge({ status }) {
  if (!status) return <span className="text-gray-400 text-xs">—</span>
  const color = SUBCHECK_COLORS[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {status}
    </span>
  )
}

function Field({ label, children }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-gray-500 font-medium">{label}</dt>
      <dd className="text-sm text-gray-800">{children}</dd>
    </div>
  )
}

export default function TicketReadinessPanel({ ticketId, projectId }) {
  const [readiness, setReadiness] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const status = readiness?.readiness_status ?? 'not_started'
  const isActive = ACTIVE_STATUSES.has(status)

  const fetchReadiness = useCallback(() => {
    api.getTicketReadiness(ticketId, projectId)
      .then(res => {
        setReadiness(res.data)
        setErr(null)
      })
      .catch(e => {
        if (e.response?.status === 404) {
          setReadiness(null)
        } else {
          setErr(e.response?.data?.detail || e.message)
        }
      })
      .finally(() => setLoading(false))
  }, [ticketId, projectId])

  useEffect(() => {
    setLoading(true)
    setReadiness(null)
    setErr(null)
    fetchReadiness()
  }, [ticketId, projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  usePolling(fetchReadiness, isActive ? POLL_INTERVAL : null, ticketId)

  const triggerEvaluation = () => {
    setBusy(true)
    setErr(null)
    api.postEvaluateReadiness(ticketId, projectId)
      .then(res => setReadiness(prev => ({ ...(prev ?? {}), ...res.data })))
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setBusy(false))
  }

  const buttonLabel = () => {
    if (busy) return 'Starting…'
    if (status === 'queued' || status === 'running') return 'Evaluation running…'
    if (status === 'failed') return 'Retry evaluation'
    if (readiness) return 'Re-evaluate readiness'
    return 'Evaluate readiness'
  }

  const reasons = readiness?.blocking_reasons ?? []
  const warnings = readiness?.warnings ?? []

  return (
    <div className="bg-white border border-gray-200 rounded p-4 space-y-4 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-700">Ticket Readiness</h2>
          {readiness && <StatusBadge status={status} />}
          {readiness?.ready_candidate && (
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
              READY CANDIDATE
            </span>
          )}
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
            Advisory only — does not gate execution
          </span>
        </div>
        <button
          onClick={triggerEvaluation}
          disabled={busy || isActive}
          className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {buttonLabel()}
        </button>
      </div>

      {err && <p className="text-red-600 text-xs">{err}</p>}

      {loading && <p className="text-gray-400 text-sm">Loading…</p>}

      {!loading && !readiness && !err && (
        <p className="text-gray-500 text-sm">
          No readiness evaluation yet. Click <em>Evaluate readiness</em> to start.
        </p>
      )}

      {isActive && (
        <p className="text-blue-600 text-sm animate-pulse">Evaluation in progress…</p>
      )}

      {readiness && status === 'ready_candidate' && reasons.length === 0 && (
        <p className="text-emerald-700 text-sm font-medium">
          No blocking issues detected.
        </p>
      )}

      {readiness && reasons.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-xs text-red-700 font-medium mb-1">Blocking reasons</p>
          <ul className="list-disc list-inside space-y-0.5">
            {reasons.map((reason, idx) => (
              <li key={idx} className="text-xs text-red-700">{reason}</li>
            ))}
          </ul>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded p-3">
          <p className="text-xs text-amber-800 font-medium mb-1">Warnings</p>
          <ul className="list-disc list-inside space-y-0.5">
            {warnings.map((w, idx) => (
              <li key={idx} className="text-xs text-amber-800">{w}</li>
            ))}
          </ul>
        </div>
      )}

      {readiness && (
        <dl className="grid grid-cols-1 sm:grid-cols-3 gap-x-6 gap-y-3">
          <Field label="Dependencies">
            <SubCheckBadge status={readiness.dependency_check_status} />
          </Field>
          <Field label="Approval">
            <SubCheckBadge status={readiness.approval_check_status} />
            {/* Advisory copy is rendered from the payload-driven warnings
                list above so the same source of truth feeds plan-review and
                execution-approval messages. No hardcoded copy here. */}
          </Field>
          <Field label="Context freshness">
            <SubCheckBadge status={readiness.context_freshness_status} />
            {readiness.main_sha_when_evaluated && (
              <p className="text-xs text-gray-500 mt-0.5 font-mono">
                main @ {readiness.main_sha_when_evaluated.slice(0, 10)}
              </p>
            )}
          </Field>

          {readiness.evaluated_at && (
            <div className="sm:col-span-3">
              <p className="text-xs text-gray-400">
                Last evaluated: {new Date(readiness.evaluated_at).toLocaleString()}
              </p>
            </div>
          )}
        </dl>
      )}
    </div>
  )
}
