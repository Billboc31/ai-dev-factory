export default function BatchPhasesPanel({ phases }) {
  if (!phases || phases.length === 0) {
    return (
      <p className="text-sm text-gray-400">No phases computed for this batch.</p>
    )
  }
  return (
    <ul className="space-y-3" data-testid="batch-phases">
      {phases.map((phase, idx) => {
        const label = phase.phase == null
          ? 'No phase assigned'
          : `Phase ${phase.phase}`
        const parallel = phase.tickets.length > 1
        return (
          <li
            key={phase.phase == null ? `null-${idx}` : `p-${phase.phase}`}
            className="border border-gray-200 rounded bg-white p-3"
          >
            <p className="text-sm font-semibold text-gray-700 mb-1">
              {label}
              {parallel && phase.phase != null && (
                <span className="ml-2 text-xs font-normal text-gray-500">
                  (parallel)
                </span>
              )}
            </p>
            <ul className="flex flex-wrap gap-2">
              {phase.tickets.map(tid => (
                <li
                  key={tid}
                  className="px-2 py-0.5 rounded bg-gray-100 text-xs font-mono text-gray-700"
                >
                  {tid}
                </li>
              ))}
            </ul>
          </li>
        )
      })}
    </ul>
  )
}
