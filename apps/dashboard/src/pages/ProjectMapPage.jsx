import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import * as mapApi from '../api/projectMap'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

const STATUS_COLORS = {
  done: 'bg-green-100 text-green-800',
  running: 'bg-yellow-100 text-yellow-800',
  waiting_human: 'bg-purple-100 text-purple-800',
  runnable: 'bg-blue-100 text-blue-800',
  blocked_dependency: 'bg-red-100 text-red-800',
  blocked_retry: 'bg-orange-100 text-orange-800',
  not_ingested: 'bg-gray-100 text-gray-600',
  unknown: 'bg-gray-100 text-gray-400',
}

function StatusBadge({ status }) {
  const cls = STATUS_COLORS[status] || STATUS_COLORS.unknown
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {status}
    </span>
  )
}

function SummaryBar({ summary }) {
  if (!summary) return null
  const items = [
    { label: 'Total', value: summary.total, color: 'text-gray-700' },
    { label: 'Runnable', value: summary.runnable, color: 'text-blue-700' },
    { label: 'Running', value: summary.running, color: 'text-yellow-700' },
    { label: 'Waiting', value: summary.waiting_human, color: 'text-purple-700' },
    { label: 'Blocked', value: summary.blocked, color: 'text-red-700' },
    { label: 'Done', value: summary.done, color: 'text-green-700' },
    { label: 'Not ingested', value: summary.not_ingested, color: 'text-gray-500' },
  ]
  return (
    <div className="flex flex-wrap gap-4 mb-6 p-4 bg-white border border-gray-200 rounded-lg">
      {items.map(({ label, value, color }) => (
        <div key={label} className="text-center">
          <div className={`text-2xl font-bold ${color}`}>{value ?? 0}</div>
          <div className="text-xs text-gray-500">{label}</div>
        </div>
      ))}
    </div>
  )
}

function TicketRow({ ticket }) {
  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="py-2 px-3 font-mono text-sm">
        {ticket.ticket_id ? (
          <Link to={`/tickets/${ticket.ticket_id}`} className="text-blue-600 hover:underline">
            {ticket.ticket_id}
          </Link>
        ) : (
          <span className="text-gray-400">—</span>
        )}
      </td>
      <td className="py-2 px-3 text-sm text-gray-500 font-mono">
        {ticket.issue_number ? `#${ticket.issue_number}` : '—'}
      </td>
      <td className="py-2 px-3 text-sm text-gray-800 max-w-xs truncate" title={ticket.title}>
        {ticket.title || '—'}
      </td>
      <td className="py-2 px-3">
        <StatusBadge status={ticket.status} />
      </td>
      <td className="py-2 px-3 text-xs text-gray-500 font-mono">
        {ticket.depends_on.length > 0 ? ticket.depends_on.join(', ') : '—'}
      </td>
      <td className="py-2 px-3 text-xs text-gray-500 font-mono">
        {ticket.blocks.length > 0 ? ticket.blocks.join(', ') : '—'}
      </td>
      <td className="py-2 px-3 text-xs text-orange-600">
        {ticket.ambiguities.length > 0 ? ticket.ambiguities[0] : ''}
      </td>
    </tr>
  )
}

function ParallelizableGroups({ groups }) {
  if (!groups || groups.length === 0) return null
  return (
    <div className="mb-6">
      <h2 className="text-lg font-semibold mb-2">Parallelizable Groups</h2>
      <div className="flex flex-wrap gap-3">
        {groups.map((group, i) => (
          <div key={i} className="bg-blue-50 border border-blue-200 rounded p-3">
            <div className="text-xs text-blue-500 mb-1 font-medium">Group {i + 1}</div>
            <div className="flex gap-2 flex-wrap">
              {group.map(tid => (
                <Link key={tid} to={`/tickets/${tid}`} className="font-mono text-sm text-blue-700 hover:underline">
                  {tid}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function CycleWarnings({ cycles }) {
  if (!cycles || cycles.length === 0) return null
  return (
    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
      <h2 className="text-sm font-semibold text-red-700 mb-2">Dependency Cycles Detected</h2>
      {cycles.map((cycle, i) => (
        <div key={i} className="text-xs font-mono text-red-600">
          {cycle.join(' → ')}
        </div>
      ))}
    </div>
  )
}

export default function ProjectMapPage() {
  const [mapData, setMapData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchMap = useCallback(() => {
    mapApi.getProjectMap()
      .then(res => { setMapData(res.data); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [])

  usePolling(fetchMap, 15000)

  const handleRefresh = () => {
    setRefreshing(true)
    mapApi.refreshProjectMap()
      .then(() => {
        setTimeout(() => {
          fetchMap()
          setRefreshing(false)
        }, 2000)
      })
      .catch(err => {
        setError(err.response?.data?.detail || err.message)
        setRefreshing(false)
      })
  }

  const blockedTickets = mapData?.tickets?.filter(t =>
    t.status === 'blocked_dependency' || t.status === 'blocked_retry'
  ) || []

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Project Map</h1>
          {mapData?.generated_at && (
            <p className="text-xs text-gray-400 mt-0.5">Last scan: {mapData.generated_at}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {mapData?.next_recommended && (
            <div className="text-sm text-gray-600">
              Next recommended:{' '}
              <Link to={`/tickets/${mapData.next_recommended}`} className="font-mono font-semibold text-blue-600 hover:underline">
                {mapData.next_recommended}
              </Link>
            </div>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {refreshing ? 'Scanning…' : 'Refresh map'}
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      {loading && !mapData && <p className="text-gray-500">Loading…</p>}

      {!loading && !mapData?.tickets?.length && (
        <div className="text-center py-12 text-gray-500">
          <p className="mb-2">No project map available yet.</p>
          <p className="text-sm">Click <strong>Refresh map</strong> to generate one.</p>
        </div>
      )}

      {mapData && (
        <>
          <SummaryBar summary={mapData.summary} />

          <CycleWarnings cycles={mapData.cycles} />

          <ParallelizableGroups groups={mapData.parallelizable_groups} />

          {blockedTickets.length > 0 && (
            <div className="mb-6">
              <h2 className="text-lg font-semibold mb-2 text-red-700">Blocked Tickets</h2>
              <div className="flex flex-wrap gap-2">
                {blockedTickets.map(t => (
                  <div key={t.ticket_id || t.issue_number} className="bg-red-50 border border-red-200 rounded px-3 py-2 text-sm">
                    <span className="font-mono font-semibold text-red-700">
                      {t.ticket_id || `#${t.issue_number}`}
                    </span>
                    <StatusBadge status={t.status} />
                    {t.depends_on.length > 0 && (
                      <span className="text-xs text-gray-500 ml-1">
                        waiting on: {t.depends_on.join(', ')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <h2 className="text-lg font-semibold mb-2">All Tickets</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left bg-white border border-gray-200 rounded-lg overflow-hidden">
                <thead className="bg-gray-50 text-xs text-gray-600 uppercase tracking-wide">
                  <tr>
                    <th className="py-2 px-3">Ticket</th>
                    <th className="py-2 px-3">Issue</th>
                    <th className="py-2 px-3">Title</th>
                    <th className="py-2 px-3">Status</th>
                    <th className="py-2 px-3">Depends on</th>
                    <th className="py-2 px-3">Blocks</th>
                    <th className="py-2 px-3">Ambiguity</th>
                  </tr>
                </thead>
                <tbody>
                  {mapData.tickets.map((t, i) => (
                    <TicketRow key={t.ticket_id || t.issue_number || i} ticket={t} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
