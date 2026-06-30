// Pure helpers that compute per-step workflow status and a top-level summary
// from the same payloads the existing ticket panels already display.
//
// No I/O, no React: kept side-effect free so it can be unit-tested in isolation
// and re-used across the timeline + global summary block.

export const STEP_KEYS = [
  'intelligence',
  'readiness',
  'approval',
  'readyToTake',
  'execution',
]

export const STEP_LABELS = {
  intelligence: 'Intelligence',
  readiness:    'Readiness',
  approval:     'Human Approval',
  readyToTake:  'Ready To Take',
  execution:    'Execution',
}

const EXECUTION_DONE_STATES = new Set([
  'IMPLEMENTATION_APPROVED',
  'TEST_COMPLETE',
  'COMPLETE',
  'COMPLETED',
  'MERGED',
  'ARCHIVED',
])

const EXECUTION_ACTIVE_STATES = new Set([
  'PLAN_APPROVED',
  'RUNNING',
  'IMPLEMENTING',
  'TESTING',
  'REVIEWING',
  'IMPLEMENTATION_REVIEW_NEEDED',
  'CONFLICT_RESOLVING',
])

const EXECUTION_BLOCKED_STATES = new Set([
  'CONFLICT_RESOLUTION_NEEDED',
  'CONFLICT_RESOLVING',
  'CONFLICT_RESOLVED_REVIEW_NEEDED',
  'CONFLICT_RESOLUTION_FAILED',
  'FAILED',
])

function isExecutionBlocked(state) {
  if (!state) return false
  if (EXECUTION_BLOCKED_STATES.has(state)) return true
  return state.endsWith('_FAILED')
}

function intelligenceStep(intelligence) {
  const status = intelligence?.analysis_status
  if (status === 'completed') {
    const parts = []
    if (intelligence?.difficulty_score != null) {
      parts.push(`Difficulty ${intelligence.difficulty_score}/10`)
    }
    if (intelligence?.risk_score != null) {
      parts.push(`Risk ${intelligence.risk_score}/10`)
    }
    return {
      status: 'done',
      summary: parts.length ? parts.join(' · ') : 'Analysis complete',
      blockingReason: null,
      nextAction: null,
    }
  }
  if (status === 'queued' || status === 'running') {
    return {
      status: 'current',
      summary: 'Analysis in progress',
      blockingReason: null,
      nextAction: 'Wait for intelligence analysis to complete',
    }
  }
  if (status === 'failed') {
    return {
      status: 'blocked',
      summary: 'Analysis failed',
      blockingReason: intelligence?.analysis_summary || 'Analysis failed',
      nextAction: 'Retry analysis',
    }
  }
  return {
    status: 'pending',
    summary: 'No analysis yet',
    blockingReason: null,
    nextAction: 'Run intelligence analysis',
  }
}

// Workflow states at or beyond PLAN_APPROVED — once the ticket has crossed
// into planner-approved territory, readiness is a historical entry gate, not
// a live re-evaluation target. The timeline renders it as passed.
const POST_READINESS_TICKET_STATES = new Set([
  'PLAN_APPROVED',
  'IMPLEMENTING',
  'IMPLEMENTATION_REVIEW_NEEDED',
  'IMPLEMENTATION_FIX_REQUIRED',
  'IMPLEMENTATION_APPROVED',
  'TESTING',
  'TEST_COMPLETE',
  'REVIEWING',
  'CONFLICT_RESOLVING',
  'CONFLICT_RESOLUTION_NEEDED',
  'CONFLICT_RESOLVED_REVIEW_NEEDED',
  'COMPLETE',
  'COMPLETED',
  'MERGED',
  'ARCHIVED',
])

function readinessStep(readiness, ticket) {
  const status = readiness?.readiness_status
  // Readiness blockers come from the API's ``blocking_reasons`` only.
  // ``warnings`` are advisory and must never demote the step to ``blocked``.
  const reasons = readiness?.blocking_reasons ?? []

  // Downstream workflow already past readiness → render as passed, do not
  // re-evaluate readiness as the gate. This keeps completed tickets coherent
  // even if their persisted readiness row is stale.
  if (ticket?.state && POST_READINESS_TICKET_STATES.has(ticket.state)) {
    return {
      status: 'done',
      summary: 'Already past readiness',
      blockingReason: null,
      nextAction: null,
    }
  }

  if (status === 'ready_candidate' || status === 'ready_to_take') {
    return {
      status: 'done',
      summary: status === 'ready_to_take' ? 'Ready to take' : 'Ready candidate',
      blockingReason: null,
      nextAction: null,
    }
  }
  if (status === 'queued' || status === 'running') {
    return {
      status: 'current',
      summary: 'Evaluation in progress',
      blockingReason: null,
      nextAction: 'Wait for readiness evaluation',
    }
  }
  if (status === 'failed') {
    return {
      status: 'blocked',
      summary: 'Evaluation failed',
      blockingReason: reasons[0] ?? 'Evaluation failed',
      nextAction: 'Resolve readiness blockers',
    }
  }
  if (status === 'blocked') {
    // Only treat as blocked when concrete entry-prerequisite blockers exist.
    // Without blockers there is nothing to act on at the readiness gate.
    if (reasons.length === 0) {
      return {
        status: 'done',
        summary: 'Ready candidate',
        blockingReason: null,
        nextAction: null,
      }
    }
    return {
      status: 'blocked',
      summary: 'Blocked',
      blockingReason: reasons[0],
      nextAction: 'Resolve readiness blockers',
    }
  }
  return {
    status: 'pending',
    summary: 'Not evaluated yet',
    blockingReason: null,
    nextAction: 'Evaluate readiness',
  }
}

function approvalStep(approval, readiness) {
  const status = approval?.approval_status
  if (status === 'approved') {
    return {
      status: 'done',
      summary: `Approved${approval?.approved_by ? ` by ${approval.approved_by}` : ''}`,
      blockingReason: null,
      nextAction: null,
    }
  }
  if (status === 'rejected') {
    return {
      status: 'blocked',
      summary: 'Rejected',
      blockingReason: approval?.approval_comment || 'Execution approval was rejected',
      nextAction: 'Revise and re-submit for approval',
    }
  }
  if (readiness?.readiness_status === 'ready_candidate') {
    return {
      status: 'current',
      summary: 'Waiting for execution approval',
      blockingReason: 'Human execution approval required',
      nextAction: 'Approve ticket for execution',
    }
  }
  return {
    status: 'pending',
    summary: 'No approval decision yet',
    blockingReason: null,
    nextAction: null,
  }
}

function readyToTakeStep(stepsSoFar) {
  const upstream = [stepsSoFar.intelligence, stepsSoFar.readiness, stepsSoFar.approval]
  if (upstream.some(s => s.status === 'blocked')) {
    return {
      status: 'blocked',
      summary: 'Blocked by upstream check',
      blockingReason: 'Resolve upstream blockers before the ticket can be taken',
      nextAction: null,
    }
  }
  if (upstream.every(s => s.status === 'done')) {
    return {
      status: 'done',
      summary: 'All checks passed',
      blockingReason: null,
      nextAction: 'Assign worker',
    }
  }
  return {
    status: 'pending',
    summary: 'Upstream checks not complete',
    blockingReason: null,
    nextAction: null,
  }
}

function executionStep(ticket) {
  const state = ticket?.state
  if (!state) {
    return {
      status: 'pending',
      summary: 'Not started',
      blockingReason: null,
      nextAction: null,
    }
  }
  if (EXECUTION_DONE_STATES.has(state)) {
    return {
      status: 'done',
      summary: `Execution complete (${state})`,
      blockingReason: null,
      nextAction: null,
    }
  }
  if (isExecutionBlocked(state)) {
    return {
      status: 'blocked',
      summary: `Execution blocked (${state})`,
      blockingReason: `Ticket is in ${state}`,
      nextAction: 'Manual intervention required',
    }
  }
  if (EXECUTION_ACTIVE_STATES.has(state)) {
    return {
      status: 'current',
      summary: `In progress (${state})`,
      blockingReason: null,
      nextAction: null,
    }
  }
  return {
    status: 'pending',
    summary: `State: ${state}`,
    blockingReason: null,
    nextAction: null,
  }
}

export function deriveStepStatuses({ intelligence, readiness, approval, ticket } = {}) {
  const steps = {
    intelligence: intelligenceStep(intelligence),
    readiness:    readinessStep(readiness, ticket),
    approval:     approvalStep(approval, readiness),
  }
  steps.readyToTake = readyToTakeStep(steps)
  steps.execution = executionStep(ticket)
  return steps
}

// Server-side eligibility status → existing UI badge label.
const ELIGIBILITY_STATUS_TO_LABEL = {
  READY_TO_TAKE:        'READY TO TAKE',
  BLOCKED:              'BLOCKED',
  WAITING_HUMAN_ACTION: 'WAITING HUMAN ACTION',
  DEPENDENCY_BLOCKED:   'DEPENDENCY BLOCKED',
  UNKNOWN:              'UNKNOWN',
}

export function eligibilityToGlobalSummary(eligibility) {
  if (!eligibility) return null
  const label = ELIGIBILITY_STATUS_TO_LABEL[eligibility.status] ?? 'UNKNOWN'
  return {
    status: label,
    reason: eligibility.reason ?? null,
    nextAction: eligibility.next_action ?? null,
  }
}

export function deriveGlobalSummary(stepStatuses) {
  if (!stepStatuses) {
    return { status: 'UNKNOWN', reason: 'No data', nextAction: null }
  }
  if (stepStatuses.execution?.status === 'done') {
    return {
      status: 'COMPLETE',
      reason: 'Execution complete',
      nextAction: null,
    }
  }
  // Walk pre-execution steps in order, surfacing the first one that blocks or is
  // actively waiting on something (a `current` upstream step is what the user
  // needs to act on next).
  const PRE_EXECUTION = ['intelligence', 'readiness', 'approval']
  for (const key of PRE_EXECUTION) {
    const step = stepStatuses[key]
    if (step?.status === 'blocked' || step?.status === 'current') {
      return {
        status: 'BLOCKED',
        reason: step.blockingReason || `Waiting on ${STEP_LABELS[key]}`,
        nextAction: step.nextAction,
      }
    }
  }
  if (stepStatuses.execution?.status === 'blocked') {
    return {
      status: 'BLOCKED',
      reason: stepStatuses.execution.blockingReason || 'Execution blocked',
      nextAction: stepStatuses.execution.nextAction,
    }
  }
  if (stepStatuses.execution?.status === 'current') {
    return {
      status: 'IN PROGRESS',
      reason: stepStatuses.execution.summary,
      nextAction: null,
    }
  }
  if (stepStatuses.readyToTake?.status === 'done') {
    return {
      status: 'READY TO TAKE',
      reason: 'All checks passed',
      nextAction: 'Assign worker',
    }
  }
  return {
    status: 'PENDING',
    reason: 'Workflow not started',
    nextAction: null,
  }
}
