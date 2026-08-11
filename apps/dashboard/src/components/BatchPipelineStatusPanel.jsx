const INTEL_BADGE = {
  not_started: 'bg-gray-100 text-gray-600',
  queued: 'bg-blue-100 text-blue-700',
  running: 'bg-indigo-100 text-indigo-700 animate-pulse',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

function statusBadgeClass(status) {
  return INTEL_BADGE[status] || 'bg-gray-100 text-gray-600'
}

function StatusBadge({ status }) {
  if (!status) return <span className="text-gray-400">—</span>
  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-medium ${statusBadgeClass(status)}`}
    >
      {status}
    </span>
  )
}

function bannerClass(waitingSummary) {
  if (!waitingSummary) return 'bg-gray-50 border-gray-200 text-gray-700'
  if (waitingSummary.startsWith('Waiting on')) return 'bg-yellow-50 border-yellow-300 text-yellow-800'
  if (waitingSummary.startsWith('Ready') || waitingSummary.includes('complete')) {
    return 'bg-green-50 border-green-300 text-green-800'
  }
  return 'bg-gray-50 border-gray-200 text-gray-700'
}

export default function BatchPipelineStatusPanel({ data }) {
  if (!data) return null
  const { waiting_summary, tickets = [] } = data

  return (
    <div
      className="bg-white rounded border border-gray-200"
      data-testid="batch-pipeline-status-panel"
    >
      <div className="p-3 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Pipeline status</h2>
        <div
          className={`border rounded px-3 py-2 text-sm font-medium ${bannerClass(waiting_summary)}`}
          data-testid="pipeline-waiting-summary"
        >
          {waiting_summary || '—'}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs" data-testid="pipeline-tickets-table">
          <thead>
            <tr className="bg-gray-50 text-left text-gray-500">
              <th className="p-2 font-medium">Ticket ID</th>
              <th className="p-2 font-medium">Title</th>
              <th className="p-2 font-medium">Intelligence</th>
              <th className="p-2 font-medium">Readiness</th>
              <th className="p-2 font-medium">Runtime state</th>
              <th className="p-2 font-medium">Blocking reason</th>
            </tr>
          </thead>
          <tbody>
            {tickets.length === 0 && (
              <tr>
                <td colSpan={6} className="p-4 text-center text-gray-400">
                  No members in this batch.
                </td>
              </tr>
            )}
            {tickets.map(ticket => (
              <tr
                key={ticket.ticket_id}
                className={`border-t border-gray-100 ${ticket.is_blocking ? 'bg-yellow-50' : ''}`}
                data-testid={`pipeline-row-${ticket.ticket_id}`}
              >
                <td className="p-2 font-mono font-medium text-gray-800">
                  {ticket.ticket_id}
                </td>
                <td className="p-2 text-gray-600 max-w-xs truncate">
                  {ticket.title || '—'}
                </td>
                <td className="p-2">
                  <StatusBadge status={ticket.intelligence_status} />
                </td>
                <td className="p-2">
                  {ticket.readiness_status
                    ? <StatusBadge status={ticket.readiness_status} />
                    : <span className="text-gray-400">—</span>}
                </td>
                <td className="p-2 text-gray-600">
                  {ticket.runtime_state || '—'}
                </td>
                <td className="p-2 text-yellow-700">
                  {ticket.blocking_reason || ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
