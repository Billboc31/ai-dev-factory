import { useCallback, useEffect, useState } from 'react'
import * as api from '../api/tickets'
import usePolling from '../hooks/usePolling'

const ACTIVE_STATUSES = new Set(['queued', 'running'])
const POLL_INTERVAL = 4000
const MAX_CONSECUTIVE_POLL_ERRORS = 5

const STAGE_LABELS = {
  queued: 'Queued',
  starting: 'Starting…',
  building_prompt: 'Building prompt',
  waiting_ai: 'Waiting for AI response',
  parsing_result: 'Parsing AI response',
  persisting: 'Saving results',
  completed: 'Completed',
  failed: 'Failed',
}

function stageLabel(stage) {
  if (!stage) return 'Running'
  return STAGE_LABELS[stage] ?? stage
}

function elapsedSeconds(startedAt) {
  if (!startedAt) return null
  const started = new Date(startedAt).getTime()
  if (Number.isNaN(started)) return null
  return Math.max(0, Math.floor((Date.now() - started) / 1000))
}

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

function Disclosure({ label, defaultOpen = false, children, dataTestId }) {
  return (
    <details
      open={defaultOpen}
      data-testid={dataTestId}
      className="border-t border-gray-100 pt-2"
    >
      <summary className="text-xs text-blue-600 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
        {label}
      </summary>
      <div className="mt-2">{children}</div>
    </details>
  )
}

function formatCost(min, max, currency) {
  if (min == null) return null
  const hi = max ?? min
  return `$${min.toFixed(3)} – $${hi.toFixed(3)} ${currency ?? 'USD'}`
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

  const highlightWarning =
    status === 'completed' &&
    intelligence &&
    (
      (intelligence.risk_score ?? 0) >= 7 ||
      intelligence.requires_human_plan_review === true ||
      intelligence.requires_human_code_review === true
    )

  const containerClass = `bg-white border ${highlightWarning ? 'border-orange-300' : 'border-gray-200'} rounded p-4 space-y-4 mb-6`

  const dependencyHints = intelligence?.dependency_hints ?? []
  const complexityFactors = intelligence?.complexity_factors ?? []

  return (
    <div className={containerClass}>
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
        <div className="text-blue-600 text-sm space-y-0.5">
          <p className="animate-pulse">Current stage: {stageLabel(intelligence?.stage)}</p>
          {intelligence?.started_at && (
            <p className="text-xs text-blue-500">
              Started: <span className="font-mono">{new Date(intelligence.started_at).toLocaleString()}</span>
            </p>
          )}
          {elapsedSeconds(intelligence?.started_at) != null && (
            <p className="text-xs text-blue-500">
              Running for: <span className="font-mono">{elapsedSeconds(intelligence.started_at)}s</span>
            </p>
          )}
        </div>
      )}

      {status === 'failed' && intelligence?.analysis_summary && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-xs text-red-700 font-medium">Analysis failed</p>
          <p className="text-xs text-red-600 mt-1">{intelligence.analysis_summary}</p>
          {intelligence.stage && intelligence.stage !== 'failed' && (
            <p className="text-xs text-red-500 mt-1">
              Failed during:{' '}
              <span className="font-mono">{stageLabel(intelligence.stage)}</span>
            </p>
          )}
          {(intelligence.failure_origin || intelligence.failed_at) && (
            <p className="text-xs text-red-500 mt-2">
              {intelligence.failure_origin && (
                <>
                  Origin:{' '}
                  <span className="font-mono">{intelligence.failure_origin}</span>
                </>
              )}
              {intelligence.failure_origin && intelligence.failed_at && ' · '}
              {intelligence.failed_at && (
                <>
                  Failed at:{' '}
                  <span className="font-mono">
                    {new Date(intelligence.failed_at).toLocaleString()}
                  </span>
                </>
              )}
            </p>
          )}
        </div>
      )}

      {status === 'completed' && intelligence && (
        <div className="space-y-3">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
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

            <Field label="Estimated cost">
              {formatCost(intelligence.estimated_cost_min, intelligence.estimated_cost_max, intelligence.cost_currency)
                ?? <span className="text-gray-400 text-xs">unknown</span>}
            </Field>

            <Field label="Recommended model">
              <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                {intelligence.recommended_model ?? '—'}
              </span>
            </Field>

            <Field label="Plan review">
              <BoolBadge value={intelligence.requires_human_plan_review} trueLabel="Required" falseLabel="Not required" />
            </Field>

            <Field label="Code review">
              <BoolBadge value={intelligence.requires_human_code_review} trueLabel="Required" falseLabel="Not required" />
            </Field>

            <Field label="Dependencies">
              {dependencyHints.length > 0 ? (
                <div className="flex flex-wrap gap-1">
                  {dependencyHints.map(dep => (
                    <span key={dep} className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">{dep}</span>
                  ))}
                </div>
              ) : (
                <span className="text-gray-400 text-xs">—</span>
              )}
            </Field>

            <Field label="Parallel safe">
              <BoolBadge value={intelligence.parallel_safe_candidate} trueLabel="Yes" falseLabel="No" />
            </Field>

            <Field label="Autonomous execution">
              <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                {intelligence.autonomous_execution_recommendation ?? '—'}
              </span>
            </Field>

            <Field label="Last analyzed">
              {intelligence.updated_at
                ? new Date(intelligence.updated_at).toLocaleString()
                : <span className="text-gray-400 text-xs">—</span>}
            </Field>
          </dl>

          {intelligence.analysis_summary && (
            <p
              className="text-sm text-gray-700 leading-relaxed line-clamp-3"
              title={intelligence.analysis_summary}
            >
              {intelligence.analysis_summary}
            </p>
          )}

          <Disclosure label="Show detailed analysis" dataTestId="detailed-analysis">
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
              {intelligence.recommended_model_reason && (
                <Field label="Recommended model reason">
                  <p className="text-xs text-gray-600">{intelligence.recommended_model_reason}</p>
                </Field>
              )}

              {intelligence.human_plan_review_reason && (
                <Field label="Plan review reason">
                  <p className="text-xs text-gray-600">{intelligence.human_plan_review_reason}</p>
                </Field>
              )}

              {intelligence.human_code_review_reason && (
                <Field label="Code review reason">
                  <p className="text-xs text-gray-600">{intelligence.human_code_review_reason}</p>
                </Field>
              )}

              {(intelligence.cost_estimate_status
                || intelligence.estimated_input_tokens != null
                || intelligence.estimated_output_tokens != null) && (
                <Field label="Cost estimate details">
                  <div className="text-xs text-gray-600 space-y-0.5">
                    {intelligence.cost_estimate_status && (
                      <p>Status: <span className="font-mono">{intelligence.cost_estimate_status}</span></p>
                    )}
                    {intelligence.estimated_input_tokens != null && (
                      <p>Input tokens: <span className="font-mono">{intelligence.estimated_input_tokens}</span></p>
                    )}
                    {intelligence.estimated_output_tokens != null && (
                      <p>Output tokens: <span className="font-mono">{intelligence.estimated_output_tokens}</span></p>
                    )}
                  </div>
                </Field>
              )}

              {intelligence.queue_rank != null && (
                <Field label="Queue rank (advisory)">
                  <span className="font-mono">#{intelligence.queue_rank}</span>
                  {intelligence.queue_reason && (
                    <p className="text-xs text-gray-500 mt-0.5">{intelligence.queue_reason}</p>
                  )}
                </Field>
              )}

              {complexityFactors.length > 0 && (
                <Field label="Complexity factors">
                  <div className="flex flex-wrap gap-1">
                    {complexityFactors.map(f => (
                      <span key={f} className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">{f}</span>
                    ))}
                  </div>
                </Field>
              )}

              {dependencyHints.length > 0 && (
                <Field label="Dependency hints (full)">
                  <div className="flex flex-wrap gap-1">
                    {dependencyHints.map(dep => (
                      <span key={dep} className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">{dep}</span>
                    ))}
                  </div>
                </Field>
              )}

              {intelligence.analysis_summary && (
                <div className="sm:col-span-2">
                  <Field label="Full analysis summary">
                    <p className="text-sm text-gray-700 leading-relaxed">{intelligence.analysis_summary}</p>
                  </Field>
                </div>
              )}
            </dl>
          </Disclosure>

          {intelligence.computed_signals_json && (
            <Disclosure label="Show raw intelligence data" dataTestId="raw-intelligence">
              <pre className="bg-gray-50 border border-gray-200 rounded p-2 text-xs overflow-auto whitespace-pre-wrap max-h-96">
                {JSON.stringify(intelligence.computed_signals_json, null, 2)}
              </pre>
            </Disclosure>
          )}
        </div>
      )}
    </div>
  )
}
