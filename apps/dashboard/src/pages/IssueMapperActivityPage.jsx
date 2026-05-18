import { useCallback, useState } from 'react'
import * as mapApi from '../api/projectMap'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

function ActivityEntry({ entry }) {
  const summary = entry.summary || {}

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 mb-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <span className="text-sm font-mono text-gray-500">{entry.timestamp}</span>
          <span className="ml-3 text-xs text-gray-400">{entry.total_issues} open issues</span>
        </div>
        {entry.next_recommended && (
          <span className="text-sm font-mono font-semibold text-blue-600">
            next: {entry.next_recommended}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm mb-3">
        <div>
          <span className="text-gray-500 text-xs uppercase font-medium">Runnable</span>
          <div className="font-mono text-blue-700 mt-0.5">
            {entry.runnable.length > 0 ? entry.runnable.join(', ') : <span className="text-gray-400">none</span>}
          </div>
        </div>
        <div>
          <span className="text-gray-500 text-xs uppercase font-medium">Blocked</span>
          <div className="font-mono text-red-700 mt-0.5">
            {entry.blocked.length > 0 ? entry.blocked.join(', ') : <span className="text-gray-400">none</span>}
          </div>
        </div>
      </div>

      {entry.parallelizable_groups.length > 0 && (
        <div className="mb-3">
          <span className="text-gray-500 text-xs uppercase font-medium">Parallelizable</span>
          <div className="flex flex-wrap gap-2 mt-1">
            {entry.parallelizable_groups.map((group, i) => (
              <span key={i} className="bg-blue-50 text-blue-700 text-xs font-mono px-2 py-0.5 rounded border border-blue-200">
                [{group.join(' + ')}]
              </span>
            ))}
          </div>
        </div>
      )}

      {entry.cycles.length > 0 && (
        <div className="mb-3 p-2 bg-red-50 rounded border border-red-200">
          <span className="text-red-600 text-xs font-semibold">Cycles detected</span>
          {entry.cycles.map((cycle, i) => (
            <div key={i} className="text-xs font-mono text-red-500 mt-0.5">
              {cycle.join(' → ')}
            </div>
          ))}
        </div>
      )}

      {entry.ambiguities.length > 0 && (
        <div className="mb-3">
          <span className="text-gray-500 text-xs uppercase font-medium">Ambiguities</span>
          <ul className="mt-1 space-y-0.5">
            {entry.ambiguities.map((a, i) => (
              <li key={i} className="text-xs text-orange-600">
                {typeof a === 'string' ? a : a.detail || JSON.stringify(a)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary && (
        <div className="flex gap-3 text-xs text-gray-500 border-t border-gray-100 pt-2 mt-2">
          {Object.entries(summary).map(([k, v]) => (
            <span key={k}>{k}: <strong>{v}</strong></span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function IssueMapperActivityPage() {
  const [activity, setActivity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchActivity = useCallback(() => {
    mapApi.getProjectMapActivity()
      .then(res => { setActivity(res.data); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [])

  usePolling(fetchActivity, 15000)

  const entries = activity?.entries || []

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Issue Mapper Activity</h1>
      <p className="text-sm text-gray-500 mb-6">History of project map scans — most recent first.</p>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      {loading && !activity && <p className="text-gray-500">Loading…</p>}

      {!loading && entries.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p className="mb-2">No activity recorded yet.</p>
          <p className="text-sm">Run the issue mapper via the <strong>Project Map</strong> page.</p>
        </div>
      )}

      {entries.map((entry, i) => (
        <ActivityEntry key={entry.timestamp || i} entry={entry} />
      ))}
    </div>
  )
}
