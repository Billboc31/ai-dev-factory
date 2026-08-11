import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  listBatches,
  getCurrentNextBatch,
  freezeBatch,
  retryBatchDependencyAnalysis,
  recomputeBatchDependencies,
  cancelBatch,
} from '../api/batches'
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

function progressLabel(progress) {
  if (!progress || progress.total == null) return '—'
  return `${progress.done || 0} / ${progress.total} done`
}

function BatchActions({ batch, projectId, onError, onAction }) {
  const status = batch.status
  const canFreeze = status === 'collecting'
  const canRetry = status === 'dependency_analysis_failed'
  const canRecompute =
    status !== 'completed' && status !== 'dispatching'
  const canCancel = status !== 'dispatching' && status !== 'completed'

  const safe = async (label, fn) => {
    try {
      await fn()
      onAction?.()
    } catch (err) {
      onError(err?.response?.data?.detail || err.message || `${label} failed`)
    }
  }

  return (
    <div className="flex gap-1 flex-wrap" role="group" aria-label="Batch actions">
      <Link
        to={projectId
          ? `/projects/${projectId}/dispatcher/batches/${batch.batch_id}`
          : `/dispatcher/batches/${batch.batch_id}`}
        className="px-2 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700"
      >
        Open
      </Link>
      <button
        disabled={!canFreeze}
        onClick={() => safe('Force freeze', () => freezeBatch(projectId, batch.batch_id))}
        className="px-2 py-1 text-xs rounded bg-slate-600 text-white hover:bg-slate-700 disabled:bg-gray-300 disabled:text-gray-500"
      >
        Force freeze
      </button>
      <button
        disabled={!canRetry}
        onClick={() => safe('Retry', () => retryBatchDependencyAnalysis(projectId, batch.batch_id))}
        className="px-2 py-1 text-xs rounded bg-amber-600 text-white hover:bg-amber-700 disabled:bg-gray-300 disabled:text-gray-500"
      >
        Retry analysis
      </button>
      <button
        disabled={!canRecompute}
        onClick={() => safe('Recompute', () => recomputeBatchDependencies(projectId, batch.batch_id))}
        className="px-2 py-1 text-xs rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-gray-300 disabled:text-gray-500"
      >
        Recompute
      </button>
      <button
        disabled={!canCancel}
        onClick={() => safe('Cancel', () => cancelBatch(projectId, batch.batch_id))}
        className="px-2 py-1 text-xs rounded bg-red-600 text-white hover:bg-red-700 disabled:bg-gray-300 disabled:text-gray-500"
      >
        Cancel
      </button>
    </div>
  )
}

function CurrentNextOverview({ overview, projectId }) {
  const current = overview?.current
  const next = overview?.next
  return (
    <section className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-3">
      <div className="border border-gray-200 bg-white rounded p-3">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
          Current batch
        </p>
        {current ? (
          <p className="text-sm">
            <Link
              to={projectId
                ? `/projects/${projectId}/dispatcher/batches/${current.batch_id}`
                : `/dispatcher/batches/${current.batch_id}`}
              className="text-blue-600 hover:underline font-mono font-medium"
            >
              {current.batch_id}
            </Link>{' '}
            <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${statusBadgeClass(current.status)}`}>
              {current.status}
            </span>
          </p>
        ) : (
          <p className="text-sm text-gray-400">No batch is currently dispatching.</p>
        )}
      </div>
      <div className="border border-gray-200 bg-white rounded p-3">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
          Next batch
        </p>
        {next ? (
          <p className="text-sm">
            <Link
              to={projectId
                ? `/projects/${projectId}/dispatcher/batches/${next.batch_id}`
                : `/dispatcher/batches/${next.batch_id}`}
              className="text-blue-600 hover:underline font-mono font-medium"
            >
              {next.batch_id}
            </Link>{' '}
            <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${statusBadgeClass(next.status)}`}>
              {next.status}
            </span>
          </p>
        ) : (
          <p className="text-sm text-gray-400">No upcoming batch.</p>
        )}
      </div>
    </section>
  )
}

export default function BatchesPage() {
  const { projectId } = useParams()
  const [batches, setBatches] = useState([])
  const [overview, setOverview] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchAll = useCallback(() => {
    Promise.all([listBatches(projectId), getCurrentNextBatch(projectId)])
      .then(([listRes, currentRes]) => {
        setBatches(listRes.data?.batches || [])
        setOverview(currentRes.data || null)
        setLastUpdated(new Date())
        setError(null)
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [projectId])

  usePolling(fetchAll, 10000, projectId)

  if (loading) return <p className="text-gray-500">Loading batches…</p>

  return (
    <div className="max-w-6xl">
      <div className="flex items-center gap-3 mb-4">
        <h1 className="text-2xl font-bold">Backlog batches</h1>
        {lastUpdated && (
          <span className="text-xs text-gray-400">
            Updated at {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      <CurrentNextOverview overview={overview} projectId={projectId} />

      <div className="bg-white rounded shadow border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-100 text-left text-gray-600">
              <th className="p-3 font-medium">Batch ID</th>
              <th className="p-3 font-medium">Status</th>
              <th className="p-3 font-medium">Ticket count</th>
              <th className="p-3 font-medium">Created at</th>
              <th className="p-3 font-medium">Last activity</th>
              <th className="p-3 font-medium">Progress</th>
              <th className="p-3 font-medium">Current phase</th>
              <th className="p-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {batches.length === 0 && (
              <tr>
                <td colSpan={8} className="p-6 text-center text-gray-400">
                  No batches yet.
                </td>
              </tr>
            )}
            {batches.map(batch => (
              <tr key={batch.batch_id} className="border-t border-gray-100">
                <td className="p-3">
                  <Link
                    to={projectId
                      ? `/projects/${projectId}/dispatcher/batches/${batch.batch_id}`
                      : `/dispatcher/batches/${batch.batch_id}`}
                    className="text-blue-600 hover:underline font-mono font-medium"
                  >
                    {batch.batch_id}
                  </Link>
                </td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusBadgeClass(batch.status)}`}>
                    {batch.status}
                  </span>
                  {batch.pipeline_summary && (
                    <p className="text-xs italic text-gray-500 mt-0.5">
                      {batch.pipeline_summary}
                    </p>
                  )}
                </td>
                <td className="p-3 text-xs">{batch.ticket_count}</td>
                <td className="p-3 text-xs text-gray-600">
                  {formatDate(batch.created_at)}
                </td>
                <td className="p-3 text-xs text-gray-600">
                  {formatDate(batch.last_activity_at)}
                </td>
                <td className="p-3 text-xs text-gray-700">
                  {progressLabel(batch.progress)}
                </td>
                <td className="p-3 text-xs text-gray-700">
                  {batch.current_phase == null ? '—' : `Phase ${batch.current_phase}`}
                </td>
                <td className="p-3">
                  <BatchActions
                    batch={batch}
                    projectId={projectId}
                    onError={setError}
                    onAction={fetchAll}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
