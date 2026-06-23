const STATUS_META = {
  done:    { icon: '✓', color: 'bg-green-100 text-green-800 border-green-200',     label: 'Done' },
  current: { icon: '⏳', color: 'bg-yellow-100 text-yellow-800 border-yellow-200',   label: 'Current' },
  blocked: { icon: '✗', color: 'bg-red-100 text-red-800 border-red-200',           label: 'Blocked' },
  pending: { icon: '○', color: 'bg-gray-100 text-gray-700 border-gray-200',         label: 'Pending' },
}

function StatusIcon({ status }) {
  const meta = STATUS_META[status] ?? STATUS_META.pending
  return (
    <span
      aria-label={meta.label}
      className={`inline-flex items-center justify-center w-7 h-7 rounded-full border text-sm font-semibold ${meta.color}`}
    >
      {meta.icon}
    </span>
  )
}

export default function TicketWorkflowStep({
  stepKey,
  label,
  status,
  summary,
  blockingReason,
  nextAction,
  defaultOpen,
  children,
}) {
  const meta = STATUS_META[status] ?? STATUS_META.pending
  return (
    <details
      open={defaultOpen}
      data-testid={`workflow-step-${stepKey}`}
      className="bg-white border border-gray-200 rounded mb-2"
    >
      <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden p-3 flex items-start gap-3">
        <StatusIcon status={status} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-800">{label}</span>
            <span className={`px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wide ${meta.color}`}>
              {meta.label}
            </span>
          </div>
          {summary && (
            <p className="text-xs text-gray-600 mt-0.5">{summary}</p>
          )}
          {blockingReason && (
            <p className="text-xs text-red-700 mt-0.5">
              <span className="font-medium">Blocked: </span>{blockingReason}
            </p>
          )}
          {nextAction && (
            <p className="text-xs text-blue-700 mt-0.5">
              <span className="font-medium">Next: </span>{nextAction}
            </p>
          )}
        </div>
        <span className="text-xs text-blue-600 self-center">Show details ▾</span>
      </summary>
      {children && (
        <div className="border-t border-gray-100 p-3">
          {children}
        </div>
      )}
    </details>
  )
}
