const STATUS_CONFIG = {
  done:         { icon: '✅', color: 'text-green-700',  bg: 'bg-green-50',  border: 'border-green-200' },
  running:      { icon: '⚙️', color: 'text-blue-700',   bg: 'bg-blue-50',   border: 'border-blue-200' },
  waiting_human:{ icon: '⏸',  color: 'text-yellow-700', bg: 'bg-yellow-50', border: 'border-yellow-200' },
  pending:      { icon: '○',  color: 'text-gray-400',   bg: 'bg-gray-50',   border: 'border-gray-200' },
  skipped:      { icon: '—',  color: 'text-gray-300',   bg: 'bg-gray-50',   border: 'border-gray-100' },
  failed:       { icon: '❌', color: 'text-red-700',    bg: 'bg-red-50',    border: 'border-red-200' },
}

export default function WorkflowTimeline({ timeline }) {
  if (!timeline) return <p className="text-gray-500 text-sm">No timeline data.</p>

  const ri = timeline.retry_info

  return (
    <div className="space-y-1">
      {timeline.steps.map((step) => {
        const cfg = STATUS_CONFIG[step.status] ?? STATUS_CONFIG.pending
        const showRetryAnnotation = step.status === 'failed' && ri
        return (
          <div
            key={step.id}
            className={`flex items-center gap-3 px-3 py-2 rounded border ${cfg.bg} ${cfg.border}`}
          >
            <span className="w-5 text-center text-sm select-none">{cfg.icon}</span>
            <span className={`text-sm font-medium ${cfg.color}`}>{step.label}</span>
            {showRetryAnnotation && (
              <span className="text-xs text-red-500 font-mono ml-1">
                attempt {ri.retry_count}{ri.failure_class ? ` — ${ri.failure_class}` : ''}
              </span>
            )}
            {step.agent && (
              <span className="text-xs text-gray-500 font-mono ml-auto">{step.agent}</span>
            )}
          </div>
        )
      })}

      {timeline.human_gate && (
        <div className="mt-3 px-3 py-2 rounded border bg-yellow-50 border-yellow-300 text-sm text-yellow-800 font-medium">
          ⏸ Waiting for human approval
        </div>
      )}

      {timeline.last_event && (
        <p className="mt-2 text-xs text-gray-400 font-mono truncate" title={timeline.last_event}>
          {timeline.last_event}
        </p>
      )}
    </div>
  )
}
