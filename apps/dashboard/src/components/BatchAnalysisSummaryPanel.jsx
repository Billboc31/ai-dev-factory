function isEmpty(summary) {
  if (!summary) return true
  if (summary.strategy) return false
  const listFields = [
    'foundation_tickets',
    'bootstrap_tickets',
    'important_inferred_dependencies',
    'parallel_opportunities',
    'conflicts_resolved',
    'warnings',
  ]
  return listFields.every(key => !summary[key] || summary[key].length === 0)
}

function BulletList({ items }) {
  return (
    <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
      {items.map((item, idx) => (
        <li key={idx}>{item}</li>
      ))}
    </ul>
  )
}

function LabeledGroup({ label, items }) {
  if (!items || items.length === 0) return null
  return (
    <div className="mb-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
        {label}
      </h3>
      <BulletList items={items} />
    </div>
  )
}

export default function BatchAnalysisSummaryPanel({ summary }) {
  const empty = isEmpty(summary)
  return (
    <details
      className="bg-white rounded border border-gray-200 p-3"
      data-testid="batch-analysis-summary"
      open={!empty}
    >
      <summary className="cursor-pointer text-sm font-semibold text-gray-700">
        Dependency Analysis Summary
        {summary?.generated_at && (
          <span className="ml-2 text-xs font-normal text-gray-400">
            generated {summary.generated_at}
          </span>
        )}
      </summary>
      <div className="mt-3">
        {empty ? (
          <p className="text-sm text-gray-400" data-testid="analysis-summary-empty">
            Analysis not available yet.
          </p>
        ) : (
          <>
            {summary.strategy && (
              <div className="mb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
                  Strategy
                </h3>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">
                  {summary.strategy}
                </p>
              </div>
            )}
            <LabeledGroup
              label="Foundation tickets"
              items={summary.foundation_tickets}
            />
            <LabeledGroup
              label="Bootstrap tickets"
              items={summary.bootstrap_tickets}
            />
            <LabeledGroup
              label="Important inferred dependencies"
              items={summary.important_inferred_dependencies}
            />
            <LabeledGroup
              label="Parallel execution opportunities"
              items={summary.parallel_opportunities}
            />
            <LabeledGroup
              label="Conflicts resolved"
              items={summary.conflicts_resolved}
            />
            <LabeledGroup label="Warnings" items={summary.warnings} />
          </>
        )}
      </div>
    </details>
  )
}
