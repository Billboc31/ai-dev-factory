import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  getBatch,
  getBatchGraph,
  getBatchPhases,
  getBatchInsights,
} from '../api/batches'
import BatchDependencyGraph, { colorClassForKey } from '../components/BatchDependencyGraph'
import BatchPhasesPanel from '../components/BatchPhasesPanel'
import DispatcherInsightsPanel from '../components/DispatcherInsightsPanel'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

const STATUS_BADGE = {
  collecting: 'bg-gray-100 text-gray-700',
  frozen: 'bg-slate-200 text-slate-800',
  dependency_analysis_running: 'bg-blue-100 text-blue-800',
  dependency_analysis_failed: 'bg-red-100 text-red-800',
  readiness_running: 'bg-amber-100 text-amber-800',
  dispatching: 'bg-purple-100 text-purple-800',
  completed: 'bg-green-100 text-green-800',
}

function statusBadgeClass(status) {
  return STATUS_BADGE[status] || 'bg-gray-100 text-gray-700'
}

function formatDate(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

function BatchHeader({ batch, projectId }) {
  return (
    <section className="mb-6 border border-gray-200 bg-white rounded p-4">
      <div className="flex items-center gap-3 mb-2">
        <h1 className="text-2xl font-bold">{batch.batch_id}</h1>
        <span className={`px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider ${statusBadgeClass(batch.status)}`}>
          {batch.status}
        </span>
        <Link
          to={projectId
            ? `/projects/${projectId}/dispatcher/batches`
            : '/dispatcher/batches'}
          className="ml-auto text-xs text-blue-600 hover:underline"
        >
          ← Back to batches
        </Link>
      </div>
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div>
          <dt className="font-semibold text-gray-500">Created</dt>
          <dd className="text-gray-700">{formatDate(batch.created_at)}</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-500">Frozen</dt>
          <dd className="text-gray-700">{formatDate(batch.frozen_at)}</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-500">Completed</dt>
          <dd className="text-gray-700">{formatDate(batch.completed_at)}</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-500">Last activity</dt>
          <dd className="text-gray-700">{formatDate(batch.last_activity_at)}</dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-500">Dependency analysis</dt>
          <dd className="text-gray-700">
            {batch.dependency_analysis_attempts || 0} attempt(s)
            {batch.last_dependency_analysis_error && (
              <span className="block text-red-600">
                {batch.last_dependency_analysis_error}
              </span>
            )}
          </dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-500">Progress</dt>
          <dd className="text-gray-700">
            {batch.progress?.done || 0} / {batch.progress?.total || 0} done
          </dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-500">Current phase</dt>
          <dd className="text-gray-700">
            {batch.current_phase == null ? '—' : `Phase ${batch.current_phase}`}
          </dd>
        </div>
        <div>
          <dt className="font-semibold text-gray-500">Freeze blocked</dt>
          <dd className="text-gray-700">
            {batch.freeze_blocked
              ? `yes (${batch.freeze_blocked_reason || 'unknown reason'})`
              : 'no'}
          </dd>
        </div>
      </dl>
    </section>
  )
}

function TicketsTable({ tickets, projectId }) {
  return (
    <div className="bg-white rounded shadow border border-gray-200 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-100 text-left text-gray-600">
            <th className="p-3 font-medium">Ticket ID</th>
            <th className="p-3 font-medium">Title</th>
            <th className="p-3 font-medium">Status</th>
            <th className="p-3 font-medium">Execution phase</th>
            <th className="p-3 font-medium">Dependencies</th>
            <th className="p-3 font-medium">Readiness state</th>
            <th className="p-3 font-medium">Dispatcher state</th>
          </tr>
        </thead>
        <tbody>
          {tickets.length === 0 && (
            <tr>
              <td colSpan={7} className="p-6 text-center text-gray-400">
                No tickets in this batch.
              </td>
            </tr>
          )}
          {tickets.map(ticket => (
            <tr key={ticket.ticket_id} className="border-t border-gray-100">
              <td className="p-3">
                <Link
                  to={projectId
                    ? `/projects/${projectId}/tickets/${ticket.ticket_id}`
                    : `/tickets/${ticket.ticket_id}`}
                  className="text-blue-600 hover:underline font-mono font-medium"
                >
                  {ticket.ticket_id}
                </Link>
              </td>
              <td className="p-3 text-xs text-gray-700">
                {ticket.title || '—'}
              </td>
              <td className="p-3 text-xs font-mono text-gray-700">
                {ticket.status || '—'}
              </td>
              <td className="p-3 text-xs">
                {ticket.execution_phase == null ? '—' : ticket.execution_phase}
              </td>
              <td className="p-3 text-xs text-gray-600">
                {ticket.depends_on?.length
                  ? ticket.depends_on.join(', ')
                  : '—'}
              </td>
              <td className="p-3 text-xs text-gray-600">
                {ticket.readiness_state || '—'}
              </td>
              <td className="p-3 text-xs text-gray-700">
                {ticket.dispatcher_state || '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function BatchDetailPage() {
  const { projectId, batchId } = useParams()
  const [detail, setDetail] = useState(null)
  const [graph, setGraph] = useState(null)
  const [phases, setPhases] = useState([])
  const [insights, setInsights] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchAll = useCallback(() => {
    Promise.all([
      getBatch(projectId, batchId),
      getBatchGraph(projectId, batchId),
      getBatchPhases(projectId, batchId),
      getBatchInsights(projectId, batchId),
    ])
      .then(([detailRes, graphRes, phasesRes, insightsRes]) => {
        setDetail(detailRes.data)
        setGraph(graphRes.data)
        setPhases(phasesRes.data?.phases || [])
        setInsights(insightsRes.data)
        setLastUpdated(new Date())
        setError(null)
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [projectId, batchId])

  usePolling(fetchAll, 10000, `${projectId}:${batchId}`)

  if (loading) return <p className="text-gray-500">Loading batch…</p>

  if (!detail) {
    return (
      <div className="max-w-4xl">
        <ErrorBanner message={error || 'Batch not found.'} onClose={() => setError(null)} />
      </div>
    )
  }

  return (
    <div className="max-w-6xl">
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <BatchHeader batch={detail.batch} projectId={projectId} />

      {lastUpdated && (
        <p className="text-xs text-gray-400 mb-4">
          Updated at {lastUpdated.toLocaleTimeString()}
        </p>
      )}

      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Tickets</h2>
        <TicketsTable tickets={detail.tickets || []} projectId={projectId} />
        <ColorLegend />
      </section>

      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Dependency graph</h2>
        <BatchDependencyGraph graph={graph} />
      </section>

      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Execution phases</h2>
        <BatchPhasesPanel phases={phases} />
      </section>

      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-2">Dispatcher insights</h2>
        <DispatcherInsightsPanel insights={insights} />
      </section>
    </div>
  )
}

function ColorLegend() {
  const items = [
    { key: 'done', label: 'done' },
    { key: 'running', label: 'running' },
    { key: 'waiting', label: 'waiting' },
    { key: 'waiting_human', label: 'waiting human' },
    { key: 'failed', label: 'failed' },
    { key: 'selected', label: 'selected by dispatcher' },
  ]
  return (
    <ul className="flex flex-wrap gap-2 mt-2" aria-label="Color legend">
      {items.map(item => (
        <li
          key={item.key}
          className={`px-2 py-0.5 rounded text-xs border ${colorClassForKey(item.key)}`}
          data-color-key={item.key}
        >
          {item.label}
        </li>
      ))}
    </ul>
  )
}
