import { getVisibleStepKeys, STEP_LABELS } from '../lib/ticketWorkflowStatus'
import TicketWorkflowStep from './TicketWorkflowStep'

const GLOBAL_STATUS_STYLES = {
  'COMPLETE':              'bg-green-100 text-green-800 border-green-200',
  'READY TO TAKE':         'bg-emerald-100 text-emerald-800 border-emerald-200',
  'BLOCKED':               'bg-red-100 text-red-800 border-red-200',
  'WAITING HUMAN ACTION':  'bg-amber-100 text-amber-800 border-amber-200',
  'DEPENDENCY BLOCKED':    'bg-orange-100 text-orange-800 border-orange-200',
  'IN PROGRESS':           'bg-blue-100 text-blue-800 border-blue-200',
  'PENDING':               'bg-gray-100 text-gray-700 border-gray-200',
  'UNKNOWN':               'bg-gray-100 text-gray-700 border-gray-200',
}

function GlobalSummary({ summary }) {
  const style = GLOBAL_STATUS_STYLES[summary?.status] ?? GLOBAL_STATUS_STYLES.UNKNOWN
  return (
    <div
      data-testid="ticket-workflow-global-summary"
      className={`rounded p-4 mb-4 border ${style}`}
    >
      <div className="text-xs uppercase tracking-wide font-medium opacity-80">Ticket status</div>
      <div className="text-lg font-bold mt-0.5">{summary?.status ?? '—'}</div>
      {summary?.reason && (
        <div className="text-sm mt-2">
          <span className="font-medium">Reason: </span>{summary.reason}
        </div>
      )}
      {summary?.nextAction && (
        <div className="text-sm mt-0.5">
          <span className="font-medium">Next action: </span>{summary.nextAction}
        </div>
      )}
    </div>
  )
}

export default function TicketWorkflowTimeline({
  stepStatuses,
  globalSummary,
  stepContent,
  requireHumanApproval = false,
}) {
  if (!stepStatuses) return null

  const visibleKeys = getVisibleStepKeys({ requireHumanApproval })

  // Auto-open the first step that is current or blocked so the user lands on the
  // step that needs attention without an extra click.
  const blockerKey = visibleKeys.find(k =>
    stepStatuses[k]?.status === 'current' || stepStatuses[k]?.status === 'blocked'
  )

  return (
    <div className="mb-6" data-testid="ticket-workflow-timeline">
      <GlobalSummary summary={globalSummary} />
      <div className="space-y-0">
        {visibleKeys.map((key, idx) => {
          const step = stepStatuses[key]
          return (
            <div key={key}>
              <TicketWorkflowStep
                stepKey={key}
                label={STEP_LABELS[key]}
                status={step?.status ?? 'pending'}
                summary={step?.summary}
                blockingReason={step?.blockingReason}
                nextAction={step?.nextAction}
                defaultOpen={key === blockerKey}
              >
                {stepContent?.[key]}
              </TicketWorkflowStep>
              {idx < visibleKeys.length - 1 && (
                <div className="flex justify-center text-gray-400 text-lg leading-none my-1" aria-hidden="true">
                  ↓
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
