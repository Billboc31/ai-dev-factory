import { useState } from 'react'
import * as api from '../../api/runtimeDashboard'
import ConfirmDialog from './ConfirmDialog'
import ProposalSummaryModal from './ProposalSummaryModal'

const STATUS_COLORS = {
  running:   'bg-green-100 text-green-700',
  active:    'bg-green-100 text-green-700',
  completed: 'bg-blue-100 text-blue-700',
  failed:    'bg-red-100 text-red-700',
}

const ACTIVE_STATUSES = new Set(['running', 'active'])

function StatusBadge({ status }) {
  const colorClass = STATUS_COLORS[status] || 'bg-gray-100 text-gray-600'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>{status}</span>
  )
}

export default function ProposalRunsTable({ runs, onDeleted }) {
  const [confirmId, setConfirmId] = useState(null)
  const [summaryId, setSummaryId] = useState(null)
  const [deleteError, setDeleteError] = useState(null)

  const handleDelete = async (id) => {
    setConfirmId(null)
    setDeleteError(null)
    try {
      await api.deleteProposalRun(id)
      onDeleted?.()
    } catch (err) {
      setDeleteError(err.response?.data?.detail || err.message)
    }
  }

  if (runs.length === 0) {
    return <p className="text-sm text-gray-400">No proposal runs found.</p>
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
              <th className="pb-2 pr-4">Proposal ID</th>
              <th className="pb-2 pr-4">Sandbox</th>
              <th className="pb-2 pr-4">Status</th>
              <th className="pb-2 pr-4">Changed Files</th>
              <th className="pb-2 pr-4">Started</th>
              <th className="pb-2 pr-4">Finished</th>
              <th className="pb-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map(run => {
              const isActive = ACTIVE_STATUSES.has(run.status)
              return (
                <tr key={run.proposal_id} className="border-b border-gray-100">
                  <td className="py-2 pr-4 font-mono text-xs text-gray-700">{run.proposal_id}</td>
                  <td className="py-2 pr-4 text-xs text-gray-500">{run.sandbox_id || '—'}</td>
                  <td className="py-2 pr-4"><StatusBadge status={run.status} /></td>
                  <td className="py-2 pr-4 text-xs text-gray-600">{run.changed_files_count}</td>
                  <td className="py-2 pr-4 text-xs text-gray-400">{run.started_at || '—'}</td>
                  <td className="py-2 pr-4 text-xs text-gray-400">{run.finished_at || '—'}</td>
                  <td className="py-2">
                    <div className="flex gap-1">
                      <button
                        className="px-2 py-1 text-xs border border-gray-300 rounded hover:bg-gray-50 text-gray-600"
                        onClick={() => setSummaryId(run.proposal_id)}
                      >
                        Open Summary
                      </button>
                      <button
                        className="px-2 py-1 text-xs border border-red-300 rounded text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed"
                        onClick={() => setConfirmId(run.proposal_id)}
                        disabled={isActive}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {summaryId && (
        <ProposalSummaryModal
          proposalId={summaryId}
          onClose={() => setSummaryId(null)}
        />
      )}

      {confirmId && (
        <ConfirmDialog
          message={`Delete proposal run "${confirmId}"? This cannot be undone.`}
          onConfirm={() => handleDelete(confirmId)}
          onCancel={() => setConfirmId(null)}
        />
      )}
    </>
  )
}
