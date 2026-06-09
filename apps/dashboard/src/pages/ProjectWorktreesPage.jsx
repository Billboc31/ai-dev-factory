import { useCallback, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getBoardData } from '../api/daemon'
import { listBranches } from '../api/projects'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

const COLUMN_LABELS = {
  running: 'Running',
  queued: 'Queued',
  backlog: 'Backlog',
  waiting: 'Waiting',
  blocked: 'Blocked',
  pr_ready: 'PR Ready',
  done: 'Done',
}

const COLUMN_COLORS = {
  running: 'bg-yellow-50 border-yellow-200',
  queued: 'bg-blue-50 border-blue-200',
  backlog: 'bg-gray-50 border-gray-200',
  waiting: 'bg-purple-50 border-purple-200',
  blocked: 'bg-red-50 border-red-200',
  pr_ready: 'bg-green-50 border-green-200',
  done: 'bg-green-50 border-green-200',
}

const STATUS_DOT = {
  running: 'bg-yellow-400',
  queued: 'bg-blue-400',
  blocked: 'bg-red-400',
  pr_ready: 'bg-green-400',
  done: 'bg-green-600',
}

function WorktreeCard({ item, columnId }) {
  return (
    <div className={`rounded border p-3 text-sm space-y-1 ${COLUMN_COLORS[columnId] || 'bg-gray-50 border-gray-200'}`}>
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[columnId] || 'bg-gray-400'}`}
          aria-hidden="true"
        />
        <code className="font-mono font-semibold text-xs">{item.ticket_id}</code>
        {item.state && (
          <span className="text-xs text-gray-500 ml-auto">{item.state}</span>
        )}
      </div>
      {item.branch && (
        <p className="text-xs text-gray-500 font-mono truncate" title={item.branch}>
          {item.branch}
        </p>
      )}
      {item.worker_cwd && (
        <p className="text-xs text-gray-400 font-mono truncate" title={item.worker_cwd}>
          cwd: {item.worker_cwd}
        </p>
      )}
      {item.worker_pid != null && (
        <p className="text-xs text-gray-400 font-mono">pid: {item.worker_pid}</p>
      )}
    </div>
  )
}

function BranchRow({ branch }) {
  return (
    <tr className="border-t border-gray-100 hover:bg-gray-50">
      <td className="p-3 font-mono text-xs text-gray-700">{branch}</td>
      <td className="p-3 text-xs text-gray-400">—</td>
    </tr>
  )
}

export default function ProjectWorktreesPage() {
  const { projectId } = useParams()
  const [columns, setColumns] = useState([])
  const [branches, setBranches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(() => {
    getBoardData(projectId)
      .then(res => { setColumns(res.data.columns || []); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
    listBranches(projectId)
      .then(res => setBranches(res.data || []))
      .catch(() => {})
  }, [projectId])

  usePolling(fetchData, 10000, projectId)

  const activeColumns = columns.filter(c => c.items && c.items.length > 0)
  const boardTicketBranches = new Set(
    columns.flatMap(c => c.items.map(i => i.branch).filter(Boolean))
  )
  const extraBranches = branches.filter(b => !boardTicketBranches.has(b))

  if (loading) return <p className="text-gray-500">Loading worktrees…</p>

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Worktrees</h1>
      <ErrorBanner message={error} onClose={() => setError(null)} />

      {activeColumns.length === 0 && branches.length === 0 && (
        <p className="text-gray-500 text-sm">No active worktrees or branches found.</p>
      )}

      {activeColumns.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">
            Daemon Board
          </h2>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {activeColumns.map(col => (
              <div key={col.id}>
                <p className="text-xs font-semibold text-gray-500 mb-2">
                  {COLUMN_LABELS[col.id] || col.id}
                  <span className="ml-1.5 text-gray-400">({col.items.length})</span>
                </p>
                <div className="space-y-2">
                  {col.items.map(item => (
                    <WorktreeCard key={item.ticket_id} item={item} columnId={col.id} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {extraBranches.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-3">
            All Branches
          </h2>
          <div className="bg-white rounded shadow border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100 text-left text-gray-600">
                  <th className="p-3 font-medium">Branch</th>
                  <th className="p-3 font-medium">Ticket</th>
                </tr>
              </thead>
              <tbody>
                {extraBranches.map(b => (
                  <BranchRow key={b} branch={b} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
