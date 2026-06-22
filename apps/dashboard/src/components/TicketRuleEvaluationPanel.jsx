import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '../api/tickets'

const STATUS_COLORS = {
  eligible: 'bg-green-100 text-green-800',
  blocked: 'bg-red-100 text-red-800',
}

function StatusBadge({ status }) {
  if (!status) return null
  const color = STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-700'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold tracking-wide uppercase ${color}`}>
      {status}
    </span>
  )
}

const POLL_DELAY_MS = 1500
const POLL_MAX_ATTEMPTS = 20

export default function TicketRuleEvaluationPanel({ ticketId, projectId }) {
  const [evaluation, setEvaluation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const pollTimerRef = useRef(null)

  const fetchEvaluation = useCallback(() => {
    return api.getTicketRuleEvaluation(ticketId, projectId)
      .then(res => {
        setEvaluation(res.data)
        setErr(null)
        return res.data
      })
      .catch(e => {
        if (e.response?.status === 404) {
          setEvaluation(null)
          return null
        }
        setErr(e.response?.data?.detail || e.message)
        return null
      })
  }, [ticketId, projectId])

  useEffect(() => {
    setLoading(true)
    setEvaluation(null)
    setErr(null)
    fetchEvaluation().finally(() => setLoading(false))
    return () => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current)
        pollTimerRef.current = null
      }
    }
  }, [ticketId, projectId, fetchEvaluation])

  const stopPolling = () => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }

  const pollUntilChanged = useCallback((previousEvaluatedAt, attempts) => {
    stopPolling()
    pollTimerRef.current = setTimeout(() => {
      fetchEvaluation().then(latest => {
        if (latest && latest.evaluated_at !== previousEvaluatedAt) {
          setBusy(false)
          return
        }
        if (attempts <= 1) {
          setBusy(false)
          return
        }
        pollUntilChanged(previousEvaluatedAt, attempts - 1)
      })
    }, POLL_DELAY_MS)
  }, [fetchEvaluation])

  const triggerEvaluation = () => {
    setBusy(true)
    setErr(null)
    const previousEvaluatedAt = evaluation?.evaluated_at ?? null
    api.postEvaluateTicketRules(ticketId, projectId)
      .then(() => {
        pollUntilChanged(previousEvaluatedAt, POLL_MAX_ATTEMPTS)
      })
      .catch(e => {
        setErr(e.response?.data?.detail || e.message)
        setBusy(false)
      })
  }

  const failedRules = evaluation?.failed_rules ?? []
  const warnings = evaluation?.warnings ?? []

  return (
    <div className="bg-white border border-gray-200 rounded p-4 space-y-4 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-700">Ticket Rule Evaluation</h2>
          {evaluation && <StatusBadge status={evaluation.eligibility_status} />}
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
            Advisory only — does not gate execution
          </span>
        </div>
        <button
          onClick={triggerEvaluation}
          disabled={busy}
          className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {busy ? 'Evaluating…' : (evaluation ? 'Re-evaluate' : 'Evaluate')}
        </button>
      </div>

      {err && <p className="text-red-600 text-xs">{err}</p>}

      {loading && <p className="text-gray-400 text-sm">Loading…</p>}

      {!loading && !evaluation && !err && (
        <p className="text-gray-500 text-sm">No rule evaluation yet.</p>
      )}

      {evaluation && failedRules.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-xs text-red-700 font-medium mb-1">Failed rules</p>
          <ul className="list-disc list-inside space-y-0.5">
            {failedRules.map((r, idx) => (
              <li key={idx} className="text-xs text-red-700">
                <span className="font-mono">{r.rule_key}</span>: {r.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {evaluation && warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded p-3">
          <p className="text-xs text-amber-800 font-medium mb-1">Warnings</p>
          <ul className="list-disc list-inside space-y-0.5">
            {warnings.map((w, idx) => (
              <li key={idx} className="text-xs text-amber-800">
                <span className="font-mono">{w.rule_key}</span>: {w.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {evaluation?.evaluated_at && (
        <p className="text-xs text-gray-400">
          Last evaluated: {new Date(evaluation.evaluated_at).toLocaleString()}
        </p>
      )}
    </div>
  )
}
