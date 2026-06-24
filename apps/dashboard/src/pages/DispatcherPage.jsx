import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getDispatcherRecommendations, getDispatcherStatus } from '../api/dispatcher'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

const MODE_BADGE = {
  off: 'bg-gray-200 text-gray-700',
  advisory: 'bg-blue-100 text-blue-800',
  manual: 'bg-amber-100 text-amber-800',
  auto: 'bg-purple-100 text-purple-800',
}

function modeBadgeClass(mode) {
  return MODE_BADGE[mode] || 'bg-gray-200 text-gray-700'
}

export default function DispatcherPage() {
  const { projectId } = useParams()
  const [status, setStatus] = useState(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchAll = useCallback(() => {
    Promise.all([
      getDispatcherStatus(),
      getDispatcherRecommendations(projectId),
    ])
      .then(([statusRes, dataRes]) => {
        setStatus(statusRes.data)
        setData(dataRes.data)
        setLastUpdated(new Date())
        setError(null)
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [projectId])

  usePolling(fetchAll, 10000, projectId)

  if (loading) return <p className="text-gray-500">Loading dispatcher…</p>

  const mode = data?.mode || status?.mode || 'off'
  const disabled = mode === 'off'
  const notImplemented = data?.not_implemented === true

  return (
    <div className="max-w-5xl">
      <div className="flex items-center gap-3 mb-2">
        <h1 className="text-2xl font-bold">Dispatcher</h1>
        <span
          className={`px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider ${modeBadgeClass(mode)}`}
          title="Current dispatcher mode"
        >
          {mode}
        </span>
        {lastUpdated && (
          <span className="text-xs text-gray-400">
            Updated at {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>
      {data?.evaluated_at && !disabled && (
        <p className="text-xs text-gray-500 mb-4">
          Evaluated at {new Date(data.evaluated_at).toLocaleString()}
        </p>
      )}

      <ErrorBanner message={error} onClose={() => setError(null)} />

      {disabled && (
        <div className="rounded border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700">
          <p className="font-medium mb-1">Dispatcher is disabled.</p>
          <p>
            Set the <code className="font-mono">AI_DEV_FACTORY_DISPATCHER_MODE</code> environment variable
            to <code className="font-mono">advisory</code> or <code className="font-mono">manual</code> to
            enable read-only recommendations. The current ticket execution chain is unchanged.
          </p>
        </div>
      )}

      {!disabled && notImplemented && (
        <div className="rounded border border-purple-200 bg-purple-50 p-4 text-sm text-purple-800">
          The <span className="font-mono">auto</span> mode is reserved for future work and is not
          implemented yet. No recommendations are produced.
        </div>
      )}

      {!disabled && !notImplemented && (
        <div className="space-y-6">
          <section>
            <h2 className="text-lg font-semibold mb-2">Recommended execution queue</h2>
            <div className="bg-white rounded shadow border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-100 text-left text-gray-600">
                    <th className="p-3 font-medium">Rank</th>
                    <th className="p-3 font-medium">Ticket</th>
                    <th className="p-3 font-medium">Score</th>
                    <th className="p-3 font-medium">Difficulty</th>
                    <th className="p-3 font-medium">Queue rank</th>
                    <th className="p-3 font-medium">Reason</th>
                    {mode === 'manual' && <th className="p-3 font-medium">Action</th>}
                  </tr>
                </thead>
                <tbody>
                  {(data?.recommendations || []).map(rec => (
                    <tr key={rec.ticket_id} className="border-t border-gray-100">
                      <td className="p-3 font-mono text-xs text-gray-700">#{rec.rank}</td>
                      <td className="p-3">
                        <Link
                          to={projectId
                            ? `/projects/${projectId}/tickets/${rec.ticket_id}`
                            : `/tickets/${rec.ticket_id}`}
                          className="text-blue-600 hover:underline font-mono font-medium"
                        >
                          {rec.ticket_id}
                        </Link>
                      </td>
                      <td className="p-3 font-mono text-xs">{rec.score}</td>
                      <td className="p-3 text-xs text-gray-600">
                        {rec.intelligence?.difficulty_label || '—'}
                      </td>
                      <td className="p-3 font-mono text-xs text-gray-500">
                        {rec.intelligence?.queue_rank ?? '—'}
                      </td>
                      <td className="p-3 text-xs text-gray-600">{rec.reason || '—'}</td>
                      {mode === 'manual' && (
                        <td className="p-3">
                          <Link
                            to={projectId
                              ? `/projects/${projectId}/tickets/${rec.ticket_id}`
                              : `/tickets/${rec.ticket_id}`}
                            className="px-2 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700"
                            title="Open ticket to run via the existing run-ticket action"
                          >
                            Open
                          </Link>
                        </td>
                      )}
                    </tr>
                  ))}
                  {(!data?.recommendations || data.recommendations.length === 0) && (
                    <tr>
                      <td
                        colSpan={mode === 'manual' ? 7 : 6}
                        className="p-6 text-center text-gray-400"
                      >
                        No READY_TO_TAKE tickets right now.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold mb-2">Blocked tickets</h2>
            <div className="bg-white rounded shadow border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-100 text-left text-gray-600">
                    <th className="p-3 font-medium">Ticket</th>
                    <th className="p-3 font-medium">Status</th>
                    <th className="p-3 font-medium">Blocking step</th>
                    <th className="p-3 font-medium">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.blocked || []).map(b => (
                    <tr key={b.ticket_id} className="border-t border-gray-100">
                      <td className="p-3">
                        <Link
                          to={projectId
                            ? `/projects/${projectId}/tickets/${b.ticket_id}`
                            : `/tickets/${b.ticket_id}`}
                          className="text-blue-600 hover:underline font-mono font-medium"
                        >
                          {b.ticket_id}
                        </Link>
                      </td>
                      <td className="p-3 font-mono text-xs text-gray-600">{b.status || '—'}</td>
                      <td className="p-3 font-mono text-xs text-gray-500">
                        {b.blocking_step || '—'}
                      </td>
                      <td className="p-3 text-xs text-gray-600">{b.reason || '—'}</td>
                    </tr>
                  ))}
                  {(!data?.blocked || data.blocked.length === 0) && (
                    <tr>
                      <td colSpan={4} className="p-6 text-center text-gray-400">
                        No blocked tickets.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  )
}
