import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getTicketTimeline } from '../api/tickets'
import { stateBadgeClass } from '../lib/ticketColumns'

export default function TicketPreviewPanel({ ticket, projectId, githubRepo, onClose }) {
  const [timeline, setTimeline] = useState(null)
  const [timelineLoading, setTimelineLoading] = useState(false)
  const panelRef = useRef(null)

  useEffect(() => {
    if (!ticket) {
      setTimeline(null)
      return
    }
    setTimelineLoading(true)
    setTimeline(null)
    getTicketTimeline(ticket.ticket_id, projectId)
      .then(res => setTimeline(res.data))
      .catch(() => setTimeline(null))
      .finally(() => setTimelineLoading(false))
  }, [ticket, projectId])

  useEffect(() => {
    if (!ticket) return
    function handleClick(e) {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [ticket, onClose])

  const open = !!ticket

  return (
    <>
      {open && (
        <div className="fixed inset-0 bg-black/20 z-40" aria-hidden="true" />
      )}
      <div
        ref={panelRef}
        className={`fixed top-0 right-0 h-full w-96 bg-white shadow-2xl z-50 flex flex-col transition-transform duration-200 ${open ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {ticket && (
          <>
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <span className="font-mono font-bold text-gray-800 text-lg">{ticket.ticket_id}</span>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 text-xl leading-none"
                aria-label="Close"
              >
                ×
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 text-sm">
              <Row label="State">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${stateBadgeClass(ticket.state)}`}>
                  {ticket.state || '—'}
                </span>
              </Row>

              <Row label="Branch">
                <span className="font-mono text-xs text-gray-600 break-all">{ticket.branch || '—'}</span>
              </Row>

              {ticket.issue_number != null && (
                <Row label="Issue">
                  {githubRepo ? (
                    <a
                      href={`https://github.com/${githubRepo}/issues/${ticket.issue_number}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-600 hover:underline text-xs"
                    >
                      #{ticket.issue_number}
                    </a>
                  ) : (
                    <span className="text-gray-600 text-xs">#{ticket.issue_number}</span>
                  )}
                </Row>
              )}

              <Row label="Last activity">
                <span className="text-gray-600 text-xs">
                  {ticket.updated_at ? new Date(ticket.updated_at).toLocaleString() : '—'}
                </span>
              </Row>

              <Row label="Last log">
                <span className="text-gray-500 text-xs break-all line-clamp-3">{ticket.last_log || '—'}</span>
              </Row>

              <Row label="Last error">
                {timelineLoading ? (
                  <span className="text-gray-400 text-xs">Loading…</span>
                ) : timeline?.last_error ? (
                  <span className="text-red-600 text-xs break-all">{timeline.last_error}</span>
                ) : (
                  <span className="text-gray-400 text-xs">none</span>
                )}
              </Row>

              <Row label="Pull request">
                <Link
                  to={`/projects/${projectId}/tickets/${ticket.ticket_id}`}
                  className="text-blue-600 hover:underline text-xs"
                >
                  See ticket detail
                </Link>
              </Row>

              <Row label="Worktree">
                <span className="text-gray-400 text-xs italic">Open worktree (not yet available)</span>
              </Row>
            </div>

            <div className="px-5 py-4 border-t border-gray-200 flex flex-col gap-2">
              <Link
                to={`/projects/${projectId}/tickets/${ticket.ticket_id}`}
                className="w-full text-center px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Open ticket
              </Link>
              {ticket.issue_number != null && githubRepo && (
                <a
                  href={`https://github.com/${githubRepo}/issues/${ticket.issue_number}`}
                  target="_blank"
                  rel="noreferrer"
                  className="w-full text-center px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50"
                >
                  Open GitHub issue
                </a>
              )}
              <Link
                to={`/projects/${projectId}/tickets/${ticket.ticket_id}`}
                className="w-full text-center px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-50 text-gray-700"
              >
                Open PR (see ticket detail)
              </Link>
            </div>
          </>
        )}
      </div>
    </>
  )
}

function Row({ label, children }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</span>
      <div>{children}</div>
    </div>
  )
}
