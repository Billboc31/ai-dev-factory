import React, { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { listTickets, markConflictFailed } from '../api/tickets'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

const STATE_COLORS = {
  COMPLETE: 'bg-green-100 text-green-800',
  TEST_COMPLETE: 'bg-green-100 text-green-800',
  PLAN_REVIEW_NEEDED: 'bg-orange-100 text-orange-800 ring-1 ring-orange-300',
  IMPLEMENTATION_REVIEW_NEEDED: 'bg-orange-100 text-orange-800 ring-1 ring-orange-300',
  PLAN_FIX_REQUIRED: 'bg-orange-50 text-orange-700',
  IMPLEMENTATION_FIX_REQUIRED: 'bg-orange-50 text-orange-700',
  PLAN_APPROVED: 'bg-blue-100 text-blue-800',
  IMPLEMENTATION_APPROVED: 'bg-blue-100 text-blue-800',
  RUNNING: 'bg-yellow-100 text-yellow-800',
  FAILED: 'bg-red-100 text-red-800',
  CONFLICT_RESOLUTION_NEEDED: 'bg-red-100 text-red-800',
  CONFLICT_RESOLVING: 'bg-yellow-100 text-yellow-800',
  CONFLICT_RESOLVED_REVIEW_NEEDED: 'bg-blue-100 text-blue-800',
  CONFLICT_RESOLUTION_FAILED: 'bg-red-200 text-red-900',
}

const CONFLICT_STATES = new Set([
  'CONFLICT_RESOLUTION_NEEDED',
  'CONFLICT_RESOLVING',
  'CONFLICT_RESOLVED_REVIEW_NEEDED',
  'CONFLICT_RESOLUTION_FAILED',
])

const REVIEW_NEEDED_STATES = new Set([
  'PLAN_REVIEW_NEEDED',
  'IMPLEMENTATION_REVIEW_NEEDED',
])

function stateBadgeClass(state) {
  if (STATE_COLORS[state]) return STATE_COLORS[state]
  const match = Object.entries(STATE_COLORS).find(([k]) => state?.includes(k))
  return match ? match[1] : 'bg-gray-100 text-gray-700'
}

function ConflictDetail({ ticket, projectId, onRefresh }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const handleMarkFailed = () => {
    setBusy(true)
    setErr(null)
    markConflictFailed(ticket.ticket_id, projectId)
      .then(() => onRefresh())
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setBusy(false))
  }

  return (
    <tr>
      <td colSpan={5} className="px-4 pb-3 pt-0 bg-red-50 border-t-0">
        <div className="rounded border border-red-200 bg-white p-3 text-sm space-y-2">
          {err && <p className="text-red-600 text-xs">{err}</p>}
          <div className="flex flex-wrap gap-4 text-xs text-gray-600">
            {ticket.conflict_detected_at && (
              <span>Detected: {new Date(ticket.conflict_detected_at).toLocaleString()}</span>
            )}
            {ticket.pre_conflict_state && (
              <span>Was: <span className="font-mono">{ticket.pre_conflict_state}</span></span>
            )}
          </div>
          {ticket.conflicted_files && ticket.conflicted_files.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-700 mb-1">PR files involved:</p>
              <ul className="list-disc list-inside space-y-0.5">
                {ticket.conflicted_files.map(f => (
                  <li key={f} className="font-mono text-xs text-gray-600">{f}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-xs text-yellow-700 font-medium">Manual resolution required before workflow can resume.</p>
          {ticket.state === 'CONFLICT_RESOLUTION_NEEDED' && (
            <button
              onClick={handleMarkFailed}
              disabled={busy}
              className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            >
              {busy ? 'Marking…' : 'Mark as Failed'}
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

export default function ProjectTicketsPage() {
  const { projectId } = useParams()
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
              <React.Fragment key={t.ticket_id}>
                <tr className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="p-3">
                    <Link
                      to={`/projects/${projectId}/tickets/${t.ticket_id}`}
                      className="text-blue-600 hover:underline font-mono font-medium"
                    >
                      {t.ticket_id}
                    </Link>
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${stateBadgeClass(t.state)}`}>
                      {t.state || '—'}
                    </span>
                    {REVIEW_NEEDED_STATES.has(t.state) && (
                      <span className="ml-2 px-2 py-0.5 rounded text-xs font-bold bg-orange-500 text-white">
                        ACTION NEEDED
                      </span>
                    )}
                    {CONFLICT_STATES.has(t.state) && (
                      <span className="ml-2 px-2 py-0.5 rounded text-xs font-bold bg-red-600 text-white">
                        CONFLICT
                      </span>
                    )}
                  </td>
                  <td className="p-3 font-mono text-xs text-gray-500">{t.branch || '—'}</td>
                  <td className="p-3 text-gray-500 text-xs">
                    {t.updated_at ? new Date(t.updated_at).toLocaleString() : '—'}
                  </td>
                  <td className="p-3 text-gray-500 text-xs max-w-xs truncate" title={t.last_log || ''}>
                    {t.last_log || '—'}
                  </td>
                </tr>
                {CONFLICT_STATES.has(t.state) && (
                  <ConflictDetail
                    ticket={t}
                    projectId={projectId}
                    onRefresh={fetchTickets}
                  />
                )}
              </React.Fragment>
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
