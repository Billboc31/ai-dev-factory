import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import * as daemonApi from '../api/daemon'
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

function BoardCard({ item }) {
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
    </div>
  )
}

function BoardColumn({ column }) {
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
          column.items.map((item, i) => <BoardCard key={item.ticket_id || item.issue_number || i} item={item} />)
        )}
      </div>
    </div>
  )
}

export default function BoardPage() {
  const [columns, setColumns] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchBoard = useCallback(() => {
    daemonApi.getBoardData()
      .then(res => { setColumns(res.data.columns); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [])

  usePolling(fetchBoard, 10000)

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Daemon Board</h1>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      {loading && !columns && <p className="text-gray-500">Loading…</p>}

      {columns && (
        <div className="flex gap-3 overflow-x-auto pb-4">
          {columns.map(col => <BoardColumn key={col.id} column={col} />)}
        </div>
      )}
    </div>
  )
}
