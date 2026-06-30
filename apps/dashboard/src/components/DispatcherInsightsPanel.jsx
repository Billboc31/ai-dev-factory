export default function DispatcherInsightsPanel({ insights }) {
  const runnable = insights?.runnable || []
  const blocked = insights?.blocked || []
  const conflicts = insights?.conflicts || []

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="batch-insights">
      <section className="border border-gray-200 rounded bg-white p-3">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Runnable tickets
        </h3>
        {runnable.length === 0 ? (
          <p className="text-xs text-gray-400">No runnable tickets.</p>
        ) : (
          <ul className="space-y-1">
            {runnable.map(tid => (
              <li key={tid} className="text-xs font-mono text-gray-700">
                {tid}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="border border-gray-200 rounded bg-white p-3">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Blocked tickets
        </h3>
        {blocked.length === 0 ? (
          <p className="text-xs text-gray-400">No blocked tickets.</p>
        ) : (
          <ul className="space-y-1">
            {blocked.map(b => (
              <li key={b.ticket_id} className="text-xs text-gray-700">
                <span className="font-mono">{b.ticket_id}</span>
                {b.blocked_by && b.blocked_by.length > 0 && (
                  <span className="ml-2 text-gray-500">
                    blocked by{' '}
                    {b.blocked_by.map((tid, idx) => (
                      <span key={tid}>
                        <span className="font-mono">{tid}</span>
                        {idx < b.blocked_by.length - 1 ? ', ' : ''}
                      </span>
                    ))}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="border border-gray-200 rounded bg-white p-3">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">
          Conflicting tickets
        </h3>
        {conflicts.length === 0 ? (
          <p className="text-xs text-gray-400">No conflicts detected.</p>
        ) : (
          <ul className="space-y-1">
            {conflicts.map(c => (
              <li key={c.ticket_id} className="text-xs text-gray-700">
                <span className="font-mono">{c.ticket_id}</span>
                {c.conflicts_with && c.conflicts_with.length > 0 && (
                  <span className="ml-2 text-gray-500">
                    conflicts with{' '}
                    {c.conflicts_with.map((tid, idx) => (
                      <span key={tid}>
                        <span className="font-mono">{tid}</span>
                        {idx < c.conflicts_with.length - 1 ? ', ' : ''}
                      </span>
                    ))}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
