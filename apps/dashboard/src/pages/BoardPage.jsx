import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import * as daemonApi from '../api/daemon'
import * as ticketsApi from '../api/tickets'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

const COLUMN_COLORS = {
  backlog: 'bg-gray-100 border-gray-300',
  queued: 'bg-blue-50 border-blue-200',
  running: 'bg-yellow-50 border-yellow-300',
  waiting_human: 'bg-purple-50 border-purple-200',
  blocked: 'bg-red-50 border-red-200',
  pr_ready: 'bg-green-50 border-green-200',
  done: 'bg-gray-50 border-gray-200',
}

const HEADER_COLORS = {
  backlog: 'text-gray-600',
  queued: 'text-blue-700',
  running: 'text-yellow-700',
  waiting_human: 'text-purple-700',
  blocked: 'text-red-700',
  pr_ready: 'text-green-700',
  done: 'text-gray-500',
}

const READINESS_BADGE = {
  ready_candidate: { label: 'READY CANDIDATE', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  ready_to_take:   { label: 'READY TO TAKE',   color: 'bg-green-100 text-green-900 border-green-300' },
  blocked:         { label: 'BLOCKED',          color: 'bg-red-100 text-red-800 border-red-200' },
}

const FILTER_OPTIONS = [
  { value: 'all',             label: 'All readiness states' },
  { value: 'ready_candidate', label: 'Ready candidate' },
  { value: 'ready_to_take',   label: 'Ready to take' },
  { value: 'blocked',         label: 'Blocked' },
]

function ReadinessBadge({ status }) {
  const entry = READINESS_BADGE[status]
  if (!entry) return null
  return (
    <span className={`inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${entry.color}`}>
      {entry.label}
    </span>
  )
}

function BoardCard({ item, readinessStatus }) {
  const label = item.ticket_id
    ? item.ticket_id
    : item.issue_number
    ? `#${item.issue_number}`
    : '—'

  const subtitle = item.title || item.state || item.branch || null
  const worktreeName = item.worker_cwd
    ? item.worker_cwd.split('/').pop()
    : null

  return (
    <div className="bg-white border border-gray-200 rounded p-2 text-sm shadow-sm">
      {item.ticket_id ? (
        <Link to={`/tickets/${item.ticket_id}`} className="font-mono font-semibold text-blue-600 hover:underline">
          {label}
        </Link>
      ) : (
        <span className="font-mono font-semibold text-gray-700">{label}</span>
      )}
      {subtitle && (
        <p className="text-gray-500 text-xs mt-0.5 truncate" title={subtitle}>{subtitle}</p>
      )}
      {item.worker_pid != null && (
        <p className="text-yellow-700 text-xs mt-0.5 font-mono">
          pid:{item.worker_pid}
          {worktreeName && <span className="text-gray-400"> · {worktreeName}</span>}
        </p>
      )}
      {readinessStatus && <ReadinessBadge status={readinessStatus} />}
    </div>
  )
}

function BoardColumn({ column, readinessByTicket }) {
  const colorClass = COLUMN_COLORS[column.id] || 'bg-gray-50 border-gray-200'
  const headerClass = HEADER_COLORS[column.id] || 'text-gray-600'

  return (
    <div className={`flex-shrink-0 w-44 border rounded-lg p-3 ${colorClass}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className={`text-xs font-semibold uppercase tracking-wide ${headerClass}`}>
          {column.label}
        </h3>
        <span className="text-xs text-gray-400 font-mono">{column.items.length}</span>
      </div>
      <div className="space-y-2">
        {column.items.length === 0 ? (
          <p className="text-xs text-gray-400 italic">empty</p>
        ) : (
          column.items.map((item, i) => (
            <BoardCard
              key={item.ticket_id || item.issue_number || i}
              item={item}
              readinessStatus={item.ticket_id ? readinessByTicket[item.ticket_id] : null}
            />
          ))
        )}
      </div>
    </div>
  )
}

export default function BoardPage({ projectId }) {
  const [columns, setColumns] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [readinessByTicket, setReadinessByTicket] = useState({})
  const [filter, setFilter] = useState('all')

  const fetchBoard = useCallback(() => {
    daemonApi.getBoardData(projectId)
      .then(res => { setColumns(res.data.columns); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [projectId])

  usePolling(fetchBoard, 10000, projectId)

  // Fetch readiness per ticket once we have columns. Per-card 404 → no readiness yet.
  useEffect(() => {
    if (!columns) return
    const ticketIds = []
    for (const col of columns) {
      for (const item of col.items) {
        if (item.ticket_id) ticketIds.push(item.ticket_id)
      }
    }
    if (ticketIds.length === 0) return

    let cancelled = false
    Promise.all(
      ticketIds.map(id =>
        ticketsApi.getTicketReadiness(id, projectId)
          .then(r => [id, r.data?.readiness_status ?? null])
          .catch(() => [id, null])
      )
    ).then(entries => {
      if (cancelled) return
      const next = {}
      for (const [id, status] of entries) {
        if (status) next[id] = status
      }
      setReadinessByTicket(next)
    })
    return () => { cancelled = true }
  }, [columns, projectId])

  const filteredColumns = useMemo(() => {
    if (!columns || filter === 'all') return columns
    return columns.map(col => ({
      ...col,
      items: col.items.filter(item => {
        if (!item.ticket_id) return false
        return readinessByTicket[item.ticket_id] === filter
      }),
    }))
  }, [columns, filter, readinessByTicket])

  return (
    <div>
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h1 className="text-2xl font-bold">Daemon Board</h1>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <span>Readiness filter:</span>
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="px-2 py-1 text-sm border border-gray-300 rounded"
          >
            {FILTER_OPTIONS.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>
      </div>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      {loading && !columns && <p className="text-gray-500">Loading…</p>}

      {filteredColumns && (
        <div className="flex gap-3 overflow-x-auto pb-4">
          {filteredColumns.map(col => (
            <BoardColumn key={col.id} column={col} readinessByTicket={readinessByTicket} />
          ))}
        </div>
      )}
    </div>
  )
}
