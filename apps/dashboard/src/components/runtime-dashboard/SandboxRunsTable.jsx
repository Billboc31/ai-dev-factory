import { useState } from 'react'
import * as api from '../../api/runtimeDashboard'
import ConfirmDialog from './ConfirmDialog'

const STATUS_COLORS = {
  running:   'bg-green-100 text-green-700',
  creating:  'bg-yellow-100 text-yellow-700',
  idle:      'bg-yellow-100 text-yellow-700',
  active:    'bg-green-100 text-green-700',
  success:   'bg-blue-100 text-blue-700',
  completed: 'bg-blue-100 text-blue-700',
  stopped:   'bg-gray-100 text-gray-700',
  failed:    'bg-red-100 text-red-700',
  error:     'bg-red-100 text-red-700',
  destroyed: 'bg-gray-200 text-gray-500',
}

const ACTIVE_STATUSES = new Set(['running', 'creating', 'active'])

function StatusBadge({ status }) {
  const colorClass = STATUS_COLORS[status] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
      {ACTIVE_STATUSES.has(status) && <span className="animate-spin inline-block">↻</span>}
      {status}
    </span>
  )
}

export default function SandboxRunsTable({ runs, onOpenLogs, onDeleted }) {
  const [confirmId, setConfirmId] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [deleteError, setDeleteError] = useState(null)

  const handleDelete = async (id) => {
    setConfirmId(null)
    setDeleting(id)
    setDeleteError(null)
    try {
      await api.deleteSandboxRun(id)
      onDeleted?.()
    } catch (err) {
      setDeleteError(err.response?.data?.detail || err.message)
    } finally {
      setDeleting(null)
    }
  }

  if (runs.length === 0) {
    return <p className="text-sm text-gray-400">No sandbox runs found.</p>
  }

  return (
    <>
      {deleteError && (
        <p className="text-xs text-red-600 mb-2">{deleteError}</p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
              <th className="pb-2 pr-4">ID</th>
              <th className="pb-2 pr-4">Status</th>
              <th className="pb-2 pr-4">Project</th>
              <th className="pb-2 pr-4">Started</th>
              <th className="pb-2 pr-4">Finished</th>
              <th className="pb-2 pr-4">Access</th>
              <th className="pb-2 pr-4">Worktree</th>
              <th className="pb-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map(run => {
              const isActive = ACTIVE_STATUSES.has(run.status)
              const urlEntries = Object.entries(run.urls || {})
              const portsStr = Object.entries(run.ports || {})
                .map(([k, v]) => `${k}:${v}`)
                .join(', ') || '—'
              return (
                <tr key={run.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4 font-mono text-xs text-gray-700">{run.id}</td>
                  <td className="py-2 pr-4"><StatusBadge status={run.status} /></td>
                  <td className="py-2 pr-4 text-xs text-gray-600">{run.project_id || '—'}</td>
                  <td className="py-2 pr-4 text-xs text-gray-400">{run.started_at || '—'}</td>
                  <td className="py-2 pr-4 text-xs text-gray-400">{run.finished_at || '—'}</td>
                  <td className="py-2 pr-4 text-xs">
                    {urlEntries.length > 0 ? (
                      <div className="flex flex-col gap-0.5">
                        {urlEntries.map(([name, url]) => (
                          <a key={name} href={url} target="_blank" rel="noopener noreferrer"
                            className="text-blue-600 hover:underline font-mono">
                            {name}
                          </a>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-400">{portsStr}</span>
                    )}
                  </td>
                  <td className="py-2 pr-4 text-xs font-mono text-gray-400 max-w-xs truncate">
                    {run.worktree_path || '—'}
                  </td>
                  <td className="py-2">
                    <div className="flex gap-1">
                      <button
                        className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 text-gray-600"
                        onClick={() => onOpenLogs?.(run.id)}
                      >
                        Open Logs
                      </button>
                      <button
                        className="px-2 py-1 text-xs border border-red-300 rounded text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed"
                        onClick={() => setConfirmId(run.id)}
                        disabled={isActive || deleting === run.id}
                      >
                        {deleting === run.id ? '…' : 'Delete'}
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {confirmId && (
        <ConfirmDialog
          message={`Delete sandbox run "${confirmId}"? This cannot be undone.`}
          onConfirm={() => handleDelete(confirmId)}
          onCancel={() => setConfirmId(null)}
        />
      )}
    </>
  )
}
