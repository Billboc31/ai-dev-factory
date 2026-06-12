import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getProject } from '../api/projects'
import { listTickets } from '../api/tickets'
import ErrorBanner from '../components/ErrorBanner'
import TicketPreviewPanel from '../components/TicketPreviewPanel'
import usePolling from '../hooks/usePolling'
import { COLUMN_DEFS, columnForState, stateBadgeClass } from '../lib/ticketColumns'

export default function ProjectTicketsPage() {
  const { projectId } = useParams()
  const [tickets, setTickets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [previewTicket, setPreviewTicket] = useState(null)
  const [githubRepo, setGithubRepo] = useState(null)

  useEffect(() => {
    getProject(projectId).then(res => {
      if (res.data?.github_repo) setGithubRepo(res.data.github_repo)
    }).catch(() => {})
  }, [projectId])

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

  const columns = Object.fromEntries(COLUMN_DEFS.map(c => [c.id, []]))
  for (const t of tickets) {
    columns[columnForState(t.state)].push(t)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-baseline gap-3 mb-4">
        <h1 className="text-2xl font-bold">Tickets</h1>
        {lastUpdated && (
          <span className="text-xs text-gray-400">
            Updated at {lastUpdated.toLocaleTimeString()}
          </span>
        )}
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="flex gap-4 overflow-x-auto flex-1 min-h-0">
        {COLUMN_DEFS.map(col => (
          <div
            key={col.id}
            className={`flex-shrink-0 w-64 rounded-lg border ${col.color} flex flex-col`}
          >
            <div className="px-3 py-2 border-b border-inherit flex items-center justify-between">
              <span className="font-semibold text-sm text-gray-700">{col.label}</span>
              <span className="text-xs text-gray-500 bg-white/60 rounded-full px-1.5 py-0.5">
                {columns[col.id].length}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {columns[col.id].length === 0 ? (
                <p className="text-xs text-gray-400 text-center py-4">Empty</p>
              ) : (
                columns[col.id].map(t => (
                  <TicketCard
                    key={t.ticket_id}
                    ticket={t}
                    isWaitingHuman={col.id === 'waiting_human'}
                    onClick={() => setPreviewTicket(t)}
                  />
                ))
              )}
            </div>
          </div>
        ))}
      </div>

      <TicketPreviewPanel
        ticket={previewTicket}
        projectId={projectId}
        githubRepo={githubRepo}
        onClose={() => setPreviewTicket(null)}
      />
    </div>
  )
}

function TicketCard({ ticket, isWaitingHuman, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded border bg-white p-3 shadow-sm hover:shadow-md transition-shadow space-y-1.5 ${
        isWaitingHuman ? 'ring-2 ring-orange-400 border-orange-300' : 'border-gray-200'
      }`}
    >
      <div className="flex items-center justify-between gap-1">
        <span className="font-mono font-semibold text-xs text-gray-800">{ticket.ticket_id}</span>
        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${stateBadgeClass(ticket.state)}`}>
          {ticket.state || '—'}
        </span>
      </div>
      {ticket.branch && (
        <p className="font-mono text-xs text-gray-400 truncate">{ticket.branch}</p>
      )}
      {ticket.last_log && (
        <p className="text-xs text-gray-500 truncate" title={ticket.last_log}>{ticket.last_log}</p>
      )}
    </button>
  )
}
