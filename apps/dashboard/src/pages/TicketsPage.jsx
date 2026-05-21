import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { listTickets } from '../api/tickets'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

const STATE_COLORS = {
  COMPLETE: 'bg-green-100 text-green-800',
  TEST_COMPLETE: 'bg-green-100 text-green-800',
  PLAN_APPROVED: 'bg-blue-100 text-blue-800',
  IMPLEMENTATION_APPROVED: 'bg-blue-100 text-blue-800',
  RUNNING: 'bg-yellow-100 text-yellow-800',
  FAILED: 'bg-red-100 text-red-800'
}

function stateBadgeClass(state) {
  const match = Object.entries(STATE_COLORS).find(([k]) => state?.includes(k))
  return match ? match[1] : 'bg-gray-100 text-gray-700'
}

export default function TicketsPage({ projectId }) {
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)

  const fetchTickets = useCallback(() => {
    listTickets(projectId)
      .then(res => {
        setTickets(res.data)
        setLastUpdated(new Date())
        setError(null)
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [projectId])

  usePolling(fetchTickets, 5000, projectId)

  if (loading) return <p className="text-gray-500">Loading tickets…</p>

  return (
    <div>
      <div className="flex items-baseline gap-3 mb-4">
        <h1 className="text-2xl font-bold">Tickets</h1>
        {lastUpdated && (
          <span className="text-xs text-gray-400">
            Updated at {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <div className="bg-white rounded shadow border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-100 text-left text-gray-600">
              <th className="p-3 font-medium">ID</th>
              <th className="p-3 font-medium">State</th>
              <th className="p-3 font-medium">Branch</th>
              <th className="p-3 font-medium">Last Update</th>
              <th className="p-3 font-medium">Last Log</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map(t => (
              <tr key={t.ticket_id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="p-3">
                  <Link
                    to={`/tickets/${t.ticket_id}`}
                    className="text-blue-600 hover:underline font-mono font-medium"
                  >
                    {t.ticket_id}
                  </Link>
                </td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${stateBadgeClass(t.state)}`}>
                    {t.state || '—'}
                  </span>
                </td>
                <td className="p-3 font-mono text-xs text-gray-500">{t.branch || '—'}</td>
                <td className="p-3 text-gray-500 text-xs">
                  {t.updated_at ? new Date(t.updated_at).toLocaleString() : '—'}
                </td>
                <td className="p-3 text-gray-500 text-xs max-w-xs truncate" title={t.last_log || ''}>
                  {t.last_log || '—'}
                </td>
              </tr>
            ))}
            {tickets.length === 0 && (
              <tr>
                <td colSpan={5} className="p-6 text-center text-gray-400">No tickets found</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
