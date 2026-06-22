import { useCallback, useEffect, useMemo, useState } from 'react'
import * as api from '../api/tickets'
import usePolling from '../hooks/usePolling'

const POLL_INTERVAL = 10000

const GROUPS = [
  { key: 'advisory',  label: 'Advisory re-runs'  },
  { key: 'approval',  label: 'Approval actions'  },
  { key: 'recovery',  label: 'Recovery actions'  },
  { key: 'dangerous', label: 'Dangerous actions' },
]

const SAFETY_COLORS = {
  low:         'bg-green-100 text-green-800',
  medium:      'bg-amber-100 text-amber-800',
  high:        'bg-orange-100 text-orange-800',
  destructive: 'bg-red-100 text-red-800',
}

function SafetyBadge({ level }) {
  const color = SAFETY_COLORS[level] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium uppercase ${color}`}>
      {level}
    </span>
  )
}

function OperationRow({ op, recommended, onClick }) {
  const disabled = !op.enabled
  const tooltip = op.disabled_reason || ''
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          onClick={() => onClick(op)}
          disabled={disabled}
          title={tooltip}
          className={`px-2 py-1 text-xs rounded ${
            disabled
              ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {op.label}
        </button>
        <SafetyBadge level={op.safety_level} />
        {recommended && (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 border border-purple-200">
            Recommended by diagnostics
          </span>
        )}
        {disabled && op.disabled_reason && (
          <span className="text-xs text-gray-500 italic">{op.disabled_reason}</span>
        )}
      </div>
    </li>
  )
}

function ConfirmationModal({ op, ticketId, onClose, onConfirm, busy }) {
  const [reason, setReason] = useState('')
  const [typedId, setTypedId] = useState('')
  const [doubleConfirm, setDoubleConfirm] = useState(false)
  const [force, setForce] = useState(false)

  const reasonOk = !op.requires_reason || reason.trim().length > 0
  const typedOk = !op.requires_typed_ticket_id || typedId.trim() === ticketId
  const doubleOk = !op.requires_double_confirmation || doubleConfirm

  const submitDisabled = busy || !reasonOk || !typedOk || !doubleOk

  return (
    <div
      role="dialog"
      aria-label={`Confirm ${op.label}`}
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
    >
      <div className="bg-white rounded shadow-lg max-w-md w-full p-4 space-y-3">
        <h3 className="text-sm font-semibold text-gray-800">
          Confirm: {op.label}
        </h3>
        <div className="flex items-center gap-2">
          <SafetyBadge level={op.safety_level} />
          <span className="text-xs text-gray-500 font-mono">{op.operation_key}</span>
        </div>

        {op.requires_reason && (
          <textarea
            placeholder="Reason (required)"
            value={reason}
            onChange={e => setReason(e.target.value)}
            disabled={busy}
            rows={3}
            className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
          />
        )}

        {op.requires_typed_ticket_id && (
          <div className="space-y-1">
            <p className="text-xs text-gray-600">
              Type the ticket id <span className="font-mono">{ticketId}</span> to confirm:
            </p>
            <input
              type="text"
              value={typedId}
              onChange={e => setTypedId(e.target.value)}
              disabled={busy}
              className="w-full px-2 py-1 text-sm border border-gray-300 rounded font-mono"
            />
          </div>
        )}

        {op.requires_double_confirmation && (
          <label className="flex items-center gap-2 text-xs text-gray-700">
            <input
              type="checkbox"
              checked={doubleConfirm}
              onChange={e => setDoubleConfirm(e.target.checked)}
              disabled={busy}
            />
            I understand this is destructive and cannot be undone.
          </label>
        )}

        {op.safety_level === 'destructive' && (
          <label className="flex items-center gap-2 text-xs text-gray-700">
            <input
              type="checkbox"
              checked={force}
              onChange={e => setForce(e.target.checked)}
              disabled={busy}
            />
            Force (override safety checks such as dirty worktree)
          </label>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            disabled={busy}
            className="px-3 py-1.5 text-xs bg-gray-200 text-gray-800 rounded hover:bg-gray-300 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm({
              reason: reason.trim() || null,
              typed_ticket_id: typedId.trim() || null,
              confirm: op.requires_double_confirmation ? doubleConfirm : true,
              force,
            })}
            disabled={submitDisabled}
            className="px-3 py-1.5 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
          >
            {busy ? 'Running…' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function TicketOperationsPanel({ ticketId, projectId }) {
  const [operations, setOperations] = useState([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(null)
  const [activeOp, setActiveOp] = useState(null)
  const [busy, setBusy] = useState(false)
  const [resultMessage, setResultMessage] = useState(null)
  const [resultKind, setResultKind] = useState(null)
  const [diagnostics, setDiagnostics] = useState(null)

  const fetchAll = useCallback(() => {
    Promise.all([
      api.listTicketOperations(ticketId, projectId),
      api.getTicketDiagnostics(ticketId, projectId).catch(e => {
        if (e.response?.status === 404) return { data: null }
        return { data: null }
      }),
    ])
      .then(([rOps, rDiag]) => {
        setOperations(rOps.data?.operations ?? [])
        setDiagnostics(rDiag.data ?? null)
        setErr(null)
      })
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [ticketId, projectId])

  useEffect(() => {
    setLoading(true)
    setOperations([])
    setErr(null)
    setResultMessage(null)
    fetchAll()
  }, [ticketId, projectId, fetchAll])

  usePolling(fetchAll, POLL_INTERVAL, ticketId)

  const recommendedKeys = useMemo(() => {
    if (!diagnostics?.recommended_actions) return new Set()
    return new Set(diagnostics.recommended_actions.map(a => a.action_key))
  }, [diagnostics])

  const grouped = useMemo(() => {
    const map = { advisory: [], approval: [], recovery: [], dangerous: [] }
    for (const op of operations) {
      if (map[op.group]) map[op.group].push(op)
    }
    return map
  }, [operations])

  const handleClickOperation = (op) => {
    setResultMessage(null)
    setResultKind(null)
    if (op.safety_level === 'low'
      && !op.requires_reason
      && !op.requires_typed_ticket_id
      && !op.requires_double_confirmation) {
      runOperation(op, { reason: null, typed_ticket_id: null, confirm: true, force: false })
      return
    }
    setActiveOp(op)
  }

  const runOperation = (op, payload) => {
    setBusy(true)
    setErr(null)
    api.executeTicketOperation(ticketId, projectId, op.operation_key, payload)
      .then(res => {
        setResultMessage(res.data?.message || 'Operation completed.')
        setResultKind('success')
        setActiveOp(null)
        fetchAll()
      })
      .catch(e => {
        const detail = e.response?.data?.detail || e.message
        setResultMessage(detail)
        setResultKind('error')
      })
      .finally(() => setBusy(false))
  }

  return (
    <div className="bg-white border border-gray-200 rounded p-4 space-y-4 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-sm font-semibold text-gray-700">Ticket Operations</h2>
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
          Manual recovery — operator-initiated only
        </span>
      </div>

      {err && <p className="text-red-600 text-xs">{err}</p>}
      {loading && <p className="text-gray-400 text-sm">Loading…</p>}

      {resultMessage && (
        <div
          className={`text-xs rounded p-2 border ${
            resultKind === 'success'
              ? 'bg-green-50 text-green-800 border-green-200'
              : 'bg-red-50 text-red-800 border-red-200'
          }`}
        >
          {resultMessage}
        </div>
      )}

      {!loading && GROUPS.map(group => {
        const items = grouped[group.key]
        if (!items || items.length === 0) return null
        return (
          <div key={group.key} className="border border-gray-200 rounded p-3">
            <p className="text-xs font-medium text-gray-700 mb-2">{group.label}</p>
            <ul className="space-y-2">
              {items.map(op => (
                <OperationRow
                  key={op.operation_key}
                  op={op}
                  recommended={recommendedKeys.has(op.operation_key)}
                  onClick={handleClickOperation}
                />
              ))}
            </ul>
          </div>
        )
      })}

      {activeOp && (
        <ConfirmationModal
          op={activeOp}
          ticketId={ticketId}
          busy={busy}
          onClose={() => { if (!busy) setActiveOp(null) }}
          onConfirm={(payload) => runOperation(activeOp, payload)}
        />
      )}
    </div>
  )
}
