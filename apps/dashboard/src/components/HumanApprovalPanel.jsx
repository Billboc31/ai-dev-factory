import { useCallback, useEffect, useState } from 'react'
import * as api from '../api/tickets'
import usePolling from '../hooks/usePolling'

const POLL_INTERVAL = 8000

const READINESS_BADGE = {
  ready_candidate: { label: 'READY CANDIDATE', color: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  ready_to_take:   { label: 'READY TO TAKE',   color: 'bg-green-100 text-green-900 border-green-300' },
  blocked:         { label: 'BLOCKED',          color: 'bg-red-100 text-red-800 border-red-200' },
}

const STATUS_LABELS = {
  pending:  'PENDING',
  approved: 'APPROVED',
  rejected: 'REJECTED',
}

const STATUS_COLORS = {
  pending:  'bg-yellow-100 text-yellow-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
}

function ReadinessBadge({ status }) {
  const entry = READINESS_BADGE[status]
  if (!entry) {
    return (
      <span className="px-2 py-0.5 rounded text-xs font-semibold border bg-gray-100 text-gray-600 border-gray-200">
        {status || 'UNKNOWN'}
      </span>
    )
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${entry.color}`}>
      {entry.label}
    </span>
  )
}

function ApprovalStatusBadge({ status }) {
  const label = STATUS_LABELS[status] ?? status
  const color = STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>{label}</span>
  )
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch (e) {
    return iso
  }
}

export default function HumanApprovalPanel({ ticketId, projectId }) {
  const [readiness, setReadiness] = useState(null)
  const [approvals, setApprovals] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [approver, setApprover] = useState('')
  const [comment, setComment] = useState('')

  const readinessStatus = readiness?.readiness_status ?? null
  const latest = approvals.length ? approvals[approvals.length - 1] : null
  const latestStatus = latest?.approval_status ?? null

  const fetchAll = useCallback(() => {
    Promise.all([
      api.getTicketReadiness(ticketId, projectId).catch(e => {
        if (e.response?.status === 404) return { data: null }
        throw e
      }),
      api.getTicketApprovals(ticketId, projectId).catch(e => {
        if (e.response?.status === 404) return { data: { approvals: [] } }
        throw e
      }),
    ])
      .then(([rRead, rApprov]) => {
        setReadiness(rRead.data)
        setApprovals(rApprov.data?.approvals ?? [])
        setErr(null)
      })
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [ticketId, projectId])

  useEffect(() => {
    setLoading(true)
    setReadiness(null)
    setApprovals([])
    setErr(null)
    fetchAll()
  }, [ticketId, projectId]) // eslint-disable-line react-hooks/exhaustive-deps

  usePolling(fetchAll, POLL_INTERVAL, ticketId)

  const canApprove =
    readinessStatus === 'ready_candidate' || latestStatus === 'approved'
  const canReject =
    readinessStatus === 'ready_candidate' || latestStatus === 'rejected'

  const submit = (apiCall) => {
    if (!approver.trim()) {
      setErr('Approver name is required')
      return
    }
    setBusy(true)
    setErr(null)
    apiCall(ticketId, projectId, {
      approved_by: approver.trim(),
      comment: comment.trim() || null,
    })
      .then(() => {
        setComment('')
        fetchAll()
      })
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setBusy(false))
  }

  const approveTooltip = canApprove
    ? ''
    : 'Approve is enabled only when readiness is ready_candidate (or replaying an existing approval).'
  const rejectTooltip = canReject
    ? ''
    : 'Reject is enabled only when readiness is ready_candidate (or replaying an existing rejection).'

  return (
    <div className="bg-white border border-gray-200 rounded p-4 space-y-4 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-700">Human Approval</h2>
          {readiness && <ReadinessBadge status={readinessStatus} />}
        </div>
      </div>

      {err && <p className="text-red-600 text-xs">{err}</p>}
      {loading && <p className="text-gray-400 text-sm">Loading…</p>}

      {!loading && (
        <>
          {latest ? (
            <div className="text-xs text-gray-600 space-y-0.5">
              <div className="flex items-center gap-2">
                <ApprovalStatusBadge status={latestStatus} />
                <span className="font-mono">{latest.approved_by || 'unknown'}</span>
                <span className="text-gray-400">·</span>
                <span>{formatDate(latest.approved_at || latest.updated_at)}</span>
              </div>
              {latest.approval_comment && (
                <p className="text-gray-700 italic">"{latest.approval_comment}"</p>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No approval decision yet.</p>
          )}

          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              <input
                type="text"
                placeholder="Your name"
                value={approver}
                onChange={e => setApprover(e.target.value)}
                disabled={busy}
                className="flex-1 min-w-[10rem] px-2 py-1 text-sm border border-gray-300 rounded"
              />
            </div>
            <textarea
              placeholder="Optional comment"
              value={comment}
              onChange={e => setComment(e.target.value)}
              disabled={busy}
              rows={2}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
            />
            <div className="flex gap-2">
              <button
                onClick={() => submit(api.approveExecution)}
                disabled={busy || !canApprove}
                title={approveTooltip}
                className="px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              >
                {busy ? 'Processing…' : 'Approve for execution'}
              </button>
              <button
                onClick={() => submit(api.rejectExecution)}
                disabled={busy || !canReject}
                title={rejectTooltip}
                className="px-3 py-1.5 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              >
                {busy ? 'Processing…' : 'Reject execution'}
              </button>
            </div>
          </div>

          {approvals.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-700 mb-1">History</p>
              <ul className="space-y-1">
                {approvals.map(a => (
                  <li
                    key={a.id}
                    className="text-xs border border-gray-200 rounded p-2 flex flex-wrap items-center gap-2"
                  >
                    <ApprovalStatusBadge status={a.approval_status} />
                    <span className="font-mono">{a.approved_by || 'unknown'}</span>
                    <span className="text-gray-400">·</span>
                    <span className="text-gray-600">{formatDate(a.approved_at || a.updated_at)}</span>
                    {a.approval_comment && (
                      <span className="text-gray-700 italic w-full">"{a.approval_comment}"</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}
