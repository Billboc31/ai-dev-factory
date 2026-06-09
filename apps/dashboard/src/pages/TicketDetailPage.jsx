import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import * as api from '../api/tickets'
import ActionButton from '../components/ActionButton'
import AuditLog from '../components/AuditLog'
import ErrorBanner from '../components/ErrorBanner'
import WorkflowTimeline from '../components/WorkflowTimeline'
import usePolling from '../hooks/usePolling'

const CONFLICT_PANEL_STATES = new Set([
  'CONFLICT_RESOLUTION_NEEDED',
  'CONFLICT_RESOLVING',
  'CONFLICT_RESOLVED_REVIEW_NEEDED',
  'CONFLICT_RESOLUTION_FAILED',
])

const TABS = ['timeline', 'overview', 'logs', 'plan', 'review', 'tests', 'artifacts', 'audit']

const TAB_FETCHERS = {
  timeline:  (id, projectId) => api.getTicketTimeline(id, projectId),
  overview:  (id, projectId) => api.getTicketTimeline(id, projectId),
  logs:      (id, projectId) => api.getTicketLogs(id, projectId),
  plan:      (id, projectId) => api.getTicketPlan(id, projectId),
  review:    (id, projectId) => api.getTicketReview(id, projectId),
  tests:     (id, projectId) => api.getTicketTests(id, projectId),
  artifacts: (id, projectId) => api.getTicketArtifacts(id, projectId),
}

function renderContent(content) {
  if (content === undefined || content === null) return ''
  if (typeof content === 'string') return content
  return JSON.stringify(content, null, 2)
}

function ConflictResolutionPanel({ ticket, projectId, onRefresh }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const state = ticket?.state

  const act = (fn) => {
    setBusy(true)
    setErr(null)
    fn()
      .then(() => onRefresh())
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setBusy(false))
  }

  if (!state || !CONFLICT_PANEL_STATES.has(state)) return null

  return (
    <div className="bg-white border border-orange-200 rounded p-4 space-y-3 mb-6">
      <h2 className="text-sm font-semibold text-orange-800">Conflict Resolution</h2>

      {err && <p className="text-red-600 text-xs">{err}</p>}

      <div className="flex flex-wrap gap-3 text-xs text-gray-600">
        {ticket.conflict_detected_at && (
          <span>Detected: {new Date(ticket.conflict_detected_at).toLocaleString()}</span>
        )}
        {ticket.pre_conflict_state && (
          <span>Was in: <span className="font-mono">{ticket.pre_conflict_state}</span></span>
        )}
      </div>

      {ticket.conflicted_files && ticket.conflicted_files.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-700 mb-1">Conflicted files:</p>
          <ul className="list-disc list-inside space-y-0.5">
            {ticket.conflicted_files.map(f => (
              <li key={f} className="font-mono text-xs text-gray-600">{f}</li>
            ))}
          </ul>
        </div>
      )}

      {state === 'CONFLICT_RESOLUTION_NEEDED' && (
        <button
          onClick={() => act(() => api.resolveConflicts(ticket.ticket_id, projectId))}
          disabled={busy}
          className="px-3 py-1.5 text-xs bg-orange-600 text-white rounded hover:bg-orange-700 disabled:opacity-50"
        >
          {busy ? 'Starting…' : 'Resolve Conflicts'}
        </button>
      )}

      {state === 'CONFLICT_RESOLVING' && (
        <p className="text-xs text-yellow-700 font-medium animate-pulse">
          Resolver running — polling for updates…
        </p>
      )}

      {state === 'CONFLICT_RESOLVED_REVIEW_NEEDED' && (
        <div className="space-y-3">
          {ticket.resolution_summary && (
            <div>
              <p className="text-xs font-medium text-gray-700 mb-1">Resolution summary:</p>
              <pre className="bg-gray-50 border border-gray-200 rounded p-2 text-xs overflow-auto whitespace-pre-wrap max-h-48">
                {ticket.resolution_summary}
              </pre>
            </div>
          )}
          {ticket.conflict_test_result && (
            <div>
              <p className="text-xs font-medium text-gray-700 mb-1">Test results:</p>
              <pre className="bg-gray-50 border border-gray-200 rounded p-2 text-xs overflow-auto whitespace-pre-wrap max-h-32">
                {ticket.conflict_test_result}
              </pre>
            </div>
          )}
          <div className="flex gap-2">
            <button
              onClick={() => act(() => api.approveConflictResolution(ticket.ticket_id, projectId))}
              disabled={busy}
              className="px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              {busy ? 'Processing…' : 'Approve Resolution'}
            </button>
            <button
              onClick={() => act(() => api.rejectConflictResolution(ticket.ticket_id, projectId))}
              disabled={busy}
              className="px-3 py-1.5 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            >
              {busy ? 'Processing…' : 'Reject Resolution'}
            </button>
          </div>
        </div>
      )}

      {state === 'CONFLICT_RESOLUTION_FAILED' && (
        <p className="text-xs text-red-700 font-medium">
          Resolution failed. Check the logs tab for details. Manual intervention is required before this ticket can proceed.
        </p>
      )}
    </div>
  )
}

function OverviewTab({ timeline }) {
  if (!timeline) return <p className="text-gray-500 text-sm">No data available.</p>
  const ri = timeline.retry_info
  return (
    <div className="space-y-4">
      {ri && (
        <div className="bg-white border border-gray-200 rounded p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Retry status</h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            <dt className="text-gray-500">Attempt</dt>
            <dd className="font-mono">{ri.retry_count}</dd>
            <dt className="text-gray-500">Failure class</dt>
            <dd className="font-mono">{ri.failure_class ?? '—'}</dd>
            <dt className="text-gray-500">Cooldown until</dt>
            <dd className="font-mono">{ri.cooldown_until ?? '—'}</dd>
          </dl>
        </div>
      )}
      {timeline.last_error && (
        <div className="bg-red-50 border border-red-200 rounded p-4">
          <h3 className="text-sm font-semibold text-red-700 mb-1">Last error</h3>
          <p className="text-xs font-mono text-red-800 break-all">{timeline.last_error}</p>
        </div>
      )}
      {!ri && !timeline.last_error && (
        <p className="text-gray-500 text-sm">No retry or error information available.</p>
      )}
    </div>
  )
}

export default function TicketDetailPage() {
  const { id, projectId } = useParams()
  const [ticket, setTicket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('timeline')
  const [tabContent, setTabContent] = useState({})
  const [tabLoading, setTabLoading] = useState(false)
  const prevStateRef = useRef(null)
  const activeTabRef = useRef(tab)

  // Reset on ticket navigation
  useEffect(() => {
    setLoading(true)
    setTicket(null)
    setError(null)
    setTab('timeline')
    setTabContent({})
    prevStateRef.current = null
  }, [id])

  useEffect(() => { activeTabRef.current = tab }, [tab])

  const fetchTicket = useCallback(() => {
    api.getTicket(id, projectId)
      .then(res => {
        const newTicket = res.data
        if (prevStateRef.current !== null && prevStateRef.current !== newTicket.state) {
          setTabContent({})
        } else if (activeTabRef.current === 'logs' || activeTabRef.current === 'timeline' || activeTabRef.current === 'overview') {
          setTabContent(prev => { const n = { ...prev }; delete n[activeTabRef.current]; return n })
        }
        prevStateRef.current = newTicket.state
        setTicket(newTicket)
        setError(null)
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [id, projectId])

  // Restart polling and fetch immediately when id changes
  usePolling(fetchTicket, 5000, id)

  useEffect(() => {
    if (tabContent[tab] !== undefined) return

    const fetcher = TAB_FETCHERS[tab]
    if (!fetcher) return

    setTabLoading(true)
    fetcher(id, projectId)
      .then(res => setTabContent(prev => ({ ...prev, [tab]: res.data })))
      .catch(err => setTabContent(prev => ({
        ...prev,
        [tab]: `Error: ${err.response?.data?.detail || err.message}`
      })))
      .finally(() => setTabLoading(false))
  }, [tab, id, projectId, tabContent])

  const refreshTicket = useCallback(() => {
    prevStateRef.current = null
    setTabContent({})
    api.getTicket(id, projectId)
      .then(res => setTicket(res.data))
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [id, projectId])

  if (loading) return <p className="text-gray-500">Loading…</p>

  if (!ticket && error) {
    return (
      <div>
        <Link to={`/projects/${projectId}/tickets`} className="text-blue-600 hover:underline text-sm">← Back</Link>
        <div className="mt-4"><ErrorBanner message={error} /></div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl">
      <Link to={`/projects/${projectId}/tickets`} className="text-blue-600 hover:underline text-sm">← Back to Tickets</Link>

      <div className="mt-4 mb-6 flex items-center gap-3">
        <h1 className="text-2xl font-bold font-mono">{id}</h1>
        {ticket?.state && (
          <span className="px-2 py-1 rounded bg-blue-100 text-blue-800 text-sm font-medium">
            {ticket.state}
          </span>
        )}
        {ticket?.branch && (
          <span className="text-xs text-gray-500 font-mono">{ticket.branch}</span>
        )}
      </div>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      {ticket && CONFLICT_PANEL_STATES.has(ticket.state) && (
        <ConflictResolutionPanel
          ticket={ticket}
          projectId={projectId}
          onRefresh={refreshTicket}
        />
      )}

      <div className="flex border-b border-gray-200 mb-4">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mb-6 min-h-32">
        {tab === 'audit'
          ? <AuditLog ticketId={id} projectId={projectId} />
          : tabLoading
            ? <p className="text-gray-500 text-sm">Loading…</p>
            : tab === 'timeline'
              ? <WorkflowTimeline timeline={tabContent.timeline} />
              : tab === 'overview'
                ? <OverviewTab timeline={tabContent.overview} />
                : <pre className="bg-white border border-gray-200 rounded p-4 text-xs overflow-auto whitespace-pre-wrap max-h-96">
                    {renderContent(tabContent[tab]) || 'No content available.'}
                  </pre>
        }
      </div>

      <div className="bg-white border border-gray-200 rounded p-4 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Workflow</h2>
          <div className="flex flex-wrap gap-2">
            <ActionButton label="Run Next" action={() => api.runNextStep(id, projectId)} onSuccess={refreshTicket} />
            <ActionButton label="Approve Plan" action={() => api.approvePlan(id, projectId)} variant="secondary" onSuccess={refreshTicket} />
            <ActionButton label="Request Plan Fix" action={() => api.requestPlanFix(id, projectId)} variant="danger" onSuccess={refreshTicket} />
            <ActionButton label="Approve Implementation" action={() => api.approveImplementation(id, projectId)} variant="secondary" onSuccess={refreshTicket} />
            <ActionButton label="Request Impl Fix" action={() => api.requestImplementationFix(id, projectId)} variant="danger" onSuccess={refreshTicket} />
          </div>
        </div>
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Git / Runtime</h2>
          <div className="flex flex-wrap gap-2">
            <ActionButton label="Commit" action={() => api.commitChanges(id, projectId)} variant="secondary" onSuccess={refreshTicket} />
            <ActionButton label="Push" action={() => api.pushChanges(id, projectId)} variant="secondary" onSuccess={refreshTicket} />
            <ActionButton label="Checkpoint" action={() => api.createCheckpoint(id, projectId)} variant="secondary" onSuccess={refreshTicket} />
            <ActionButton label="Archive daemon" action={() => api.archiveDaemon(id, projectId)} variant="danger" onSuccess={refreshTicket} />
          </div>
        </div>
      </div>
    </div>
  )
}
