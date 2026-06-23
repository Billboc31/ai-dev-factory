import { useCallback, useEffect, useState } from 'react'
import * as api from '../api/tickets'
import usePolling from '../hooks/usePolling'

const ACTIVE_STATUSES = new Set(['queued', 'running'])
const POLL_INTERVAL = 4000
const MAX_CONSECUTIVE_POLL_ERRORS = 5

function StatusBadge({ status }) {
  const colors = {
    not_started: 'bg-gray-100 text-gray-600',
    queued:      'bg-yellow-100 text-yellow-800',
    running:     'bg-blue-100 text-blue-800 animate-pulse',
    completed:   'bg-green-100 text-green-800',
    failed:      'bg-red-100 text-red-800',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {status}
    </span>
  )
}

function ScoreBadge({ score, label, colorClass }) {
  if (score == null) return <span className="text-gray-400 text-xs">—</span>
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {label} ({score}/10)
    </span>
  )
}

function difficultyColor(score) {
  if (score <= 2) return 'bg-green-100 text-green-800'
  if (score <= 4) return 'bg-lime-100 text-lime-800'
  if (score <= 6) return 'bg-yellow-100 text-yellow-800'
  if (score <= 8) return 'bg-orange-100 text-orange-800'
  return 'bg-red-100 text-red-800'
}

function riskColor(score) {
  if (score <= 3) return 'bg-green-100 text-green-800'
  if (score <= 5) return 'bg-yellow-100 text-yellow-800'
  if (score <= 7) return 'bg-orange-100 text-orange-800'
  return 'bg-red-100 text-red-800'
}

function Field({ label, children }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-gray-500 font-medium">{label}</dt>
      <dd className="text-sm text-gray-800">{children}</dd>
    </div>
  )
}

function BoolBadge({ value, trueLabel = 'Yes', falseLabel = 'No' }) {
  if (value == null) return <span className="text-gray-400 text-xs">—</span>
  return value
    ? <span className="px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-800">{trueLabel}</span>
    : <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">{falseLabel}</span>
}

export default function TicketIntelligencePanel({ ticketId, projectId }) {
  const [intelligence, setIntelligence] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [pollErrorCount, setPollErrorCount] = useState(0)

  const status = intelligence?.analysis_status ?? 'not_started'
  const pollingHalted = pollErrorCount >= MAX_CONSECUTIVE_POLL_ERRORS
  const isActive = ACTIVE_STATUSES.has(status) && !pollingHalted

  const fetchIntelligence = useCallback(() => {
    api.getTicketIntelligence(ticketId, projectId)
      .then(res => {
        setIntelligence(res.data)
        setErr(null)
        setPollErrorCount(0)
      })
      .catch(e => {
        if (e.response?.status === 404) {
          setIntelligence(null)
          setPollErrorCount(0)
        } else {
          setErr(e.response?.data?.detail || e.message)
          setPollErrorCount(c => c + 1)
        }
      })
      .finally(() => setLoading(false))
  }, [ticketId, projectId])

  useEffect(() => {
    setLoading(true)
    setIntelligence(null)
    setErr(null)
    setPollErrorCount(0)
    fetchIntelligence()
  }, [ticketId, projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Poll while analysis is active; stop after MAX_CONSECUTIVE_POLL_ERRORS to
  // avoid an infinite 5xx loop when the server is unreachable.
  usePolling(fetchIntelligence, isActive ? POLL_INTERVAL : null, ticketId)

  const triggerAnalysis = () => {
    setBusy(true)
    setErr(null)
    api.analyzeTicketIntelligence(ticketId, projectId)
      .then(res => setIntelligence(res.data))
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setBusy(false))
  }

  const analyzeLabel = () => {
    if (busy) return 'Starting…'
    if (status === 'queued' || status === 'running') return 'Analysis running…'
    if (status === 'failed') return 'Retry analysis'
    if (status === 'completed') return 'Re-analyze'
    return 'Analyze'
  }

  return (
    <div className="bg-white border border-gray-200 rounded p-4 space-y-4 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-700">Ticket Intelligence</h2>
          {intelligence && <StatusBadge status={status} />}
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
            Advisory only — not used by scheduler yet
          </span>
        </div>
        <button
          onClick={triggerAnalysis}
          disabled={busy || isActive}
          className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {analyzeLabel()}
        </button>
      </div>

      {err && <p className="text-red-600 text-xs">{err}</p>}

      {pollingHalted && (
        <p className="text-red-700 text-xs font-medium">
          Polling halted — server unreachable after {MAX_CONSECUTIVE_POLL_ERRORS} consecutive failures.
        </p>
      )}

      {loading && (
        <p className="text-gray-400 text-sm">Loading…</p>
      )}

      {!loading && !intelligence && !err && (
        <p className="text-gray-500 text-sm">No analysis yet. Click Analyze to start.</p>
      )}

      {isActive && (
        <p className="text-blue-600 text-sm animate-pulse">Analysis in progress…</p>
      )}

      {status === 'failed' && intelligence?.analysis_summary && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-xs text-red-700 font-medium">Analysis failed</p>
          <p className="text-xs text-red-600 mt-1">{intelligence.analysis_summary}</p>
        </div>
      )}

      {status === 'completed' && intelligence && (
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
          <Field label="Difficulty">
            <ScoreBadge
              score={intelligence.difficulty_score}
              label={intelligence.difficulty_label ?? '—'}
              colorClass={difficultyColor(intelligence.difficulty_score ?? 5)}
            />
          </Field>

          <Field label="Risk">
            <ScoreBadge
              score={intelligence.risk_score}
              label={intelligence.risk_label ?? '—'}
              colorClass={riskColor(intelligence.risk_score ?? 5)}
            />
          </Field>

          <Field label="Recommended model">
            <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">
              {intelligence.recommended_model ?? '—'}
            </span>
            {intelligence.recommended_model_reason && (
              <p className="text-xs text-gray-500 mt-0.5">{intelligence.recommended_model_reason}</p>
            )}
          </Field>

          <Field label="Estimated cost">
            {intelligence.estimated_cost_min != null
              ? `$${intelligence.estimated_cost_min.toFixed(3)} – $${(intelligence.estimated_cost_max ?? intelligence.estimated_cost_min).toFixed(3)} ${intelligence.cost_currency ?? 'USD'}`
              : <span className="text-gray-400 text-xs">unknown</span>}
          </Field>

          <Field label="Queue rank (advisory)">
            {intelligence.queue_rank != null
              ? <>
                  <span className="font-mono">#{intelligence.queue_rank}</span>
                  {intelligence.queue_reason && (
                    <p className="text-xs text-gray-500 mt-0.5">{intelligence.queue_reason}</p>
                  )}
                </>
              : <span className="text-gray-400 text-xs">—</span>}
          </Field>

          <Field label="Autonomous execution">
            <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">
              {intelligence.autonomous_execution_recommendation ?? '—'}
            </span>
          </Field>

          <Field label="Human plan review">
            <BoolBadge value={intelligence.requires_human_plan_review} trueLabel="Required" falseLabel="Not required" />
            {intelligence.human_plan_review_reason && (
              <p className="text-xs text-gray-500 mt-0.5">{intelligence.human_plan_review_reason}</p>
            )}
          </Field>

          <Field label="Human code review">
            <BoolBadge value={intelligence.requires_human_code_review} trueLabel="Required" falseLabel="Not required" />
            {intelligence.human_code_review_reason && (
              <p className="text-xs text-gray-500 mt-0.5">{intelligence.human_code_review_reason}</p>
            )}
          </Field>

          {intelligence.dependency_hints && intelligence.dependency_hints.length > 0 && (
            <Field label="Dependency hints">
              <div className="flex flex-wrap gap-1">
                {intelligence.dependency_hints.map(dep => (
                  <span key={dep} className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">{dep}</span>
                ))}
              </div>
            </Field>
          )}

          {intelligence.complexity_factors && intelligence.complexity_factors.length > 0 && (
            <Field label="Complexity factors">
              <div className="flex flex-wrap gap-1">
                {intelligence.complexity_factors.map(f => (
                  <span key={f} className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">{f}</span>
                ))}
              </div>
            </Field>
          )}

          {intelligence.analysis_summary && (
            <div className="sm:col-span-2">
              <Field label="Summary">
                <p className="text-sm text-gray-700 leading-relaxed">{intelligence.analysis_summary}</p>
              </Field>
            </div>
          )}

          {intelligence.updated_at && (
            <div className="sm:col-span-2">
              <p className="text-xs text-gray-400">
                Last analyzed: {new Date(intelligence.updated_at).toLocaleString()}
              </p>
            </div>
          )}
        </dl>
      )}
    </div>
  )
}
