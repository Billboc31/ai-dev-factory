import { describe, expect, it } from 'vitest'
import {
  STEP_KEYS,
  deriveGlobalSummary,
  deriveStepStatuses,
  eligibilityToGlobalSummary,
} from '../src/lib/ticketWorkflowStatus'

describe('deriveStepStatuses', () => {
  it('returns all pending when nothing has started', () => {
    const steps = deriveStepStatuses({})
    expect(Object.keys(steps).sort()).toEqual([...STEP_KEYS].sort())
    expect(steps.intelligence.status).toBe('pending')
    expect(steps.readiness.status).toBe('pending')
    expect(steps.approval.status).toBe('pending')
    expect(steps.readyToTake.status).toBe('pending')
    expect(steps.execution.status).toBe('pending')
  })

  it('marks intelligence as current when analysis is running', () => {
    const steps = deriveStepStatuses({ intelligence: { analysis_status: 'running' } })
    expect(steps.intelligence.status).toBe('current')
    expect(steps.intelligence.summary).toMatch(/in progress/i)
  })

  it('marks intelligence as done with difficulty/risk summary when completed', () => {
    const steps = deriveStepStatuses({
      intelligence: {
        analysis_status: 'completed',
        difficulty_score: 7,
        risk_score: 4,
      },
    })
    expect(steps.intelligence.status).toBe('done')
    expect(steps.intelligence.summary).toMatch(/Difficulty 7\/10/)
    expect(steps.intelligence.summary).toMatch(/Risk 4\/10/)
  })

  it('marks readiness as blocked and surfaces first blocking reason', () => {
    const steps = deriveStepStatuses({
      readiness: {
        readiness_status: 'blocked',
        blocking_reasons: ['Dependency T999 not merged', 'stale context'],
      },
    })
    expect(steps.readiness.status).toBe('blocked')
    expect(steps.readiness.blockingReason).toBe('Dependency T999 not merged')
  })

  // ── T213 entry-prerequisite contract ──────────────────────────────────────

  it('keeps readiness as done when ready_candidate carries only advisory warnings', () => {
    const steps = deriveStepStatuses({
      readiness: {
        readiness_status: 'ready_candidate',
        blocking_reasons: [],
        warnings: ['Human plan review may be required later'],
      },
    })
    expect(steps.readiness.status).toBe('done')
    expect(steps.readiness.blockingReason).toBeNull()
  })

  it('treats ready_to_take as done in the readiness step', () => {
    const steps = deriveStepStatuses({
      readiness: { readiness_status: 'ready_to_take' },
    })
    expect(steps.readiness.status).toBe('done')
    expect(steps.readiness.summary).toMatch(/ready to take/i)
  })

  it('does not flip readiness to blocked when blocked status has no concrete blockers', () => {
    // Defensive: stale persisted row claims "blocked" but provides no
    // entry-prerequisite blocker. The step must not surface as BLOCKED.
    const steps = deriveStepStatuses({
      readiness: {
        readiness_status: 'blocked',
        blocking_reasons: [],
      },
    })
    expect(steps.readiness.status).toBe('done')
  })

  it('renders readiness as done for completed tickets regardless of payload', () => {
    // Completed ticket (downstream state ≥ PLAN_APPROVED) → readiness is a
    // historical entry gate, not a live re-evaluation target.
    for (const state of ['PLAN_APPROVED', 'IMPLEMENTATION_APPROVED', 'MERGED']) {
      const steps = deriveStepStatuses({
        readiness: {
          readiness_status: 'blocked',
          blocking_reasons: ['stale blocker'],
        },
        ticket: { state },
      })
      expect(steps.readiness.status).toBe('done')
      expect(steps.readiness.blockingReason).toBeNull()
    }
  })

  it('marks approval as current when readiness is ready_candidate and no approval yet', () => {
    const steps = deriveStepStatuses({
      readiness: { readiness_status: 'ready_candidate' },
      approval: null,
    })
    expect(steps.approval.status).toBe('current')
    expect(steps.approval.blockingReason).toBe('Human plan approval required')
    expect(steps.approval.nextAction).toBe('Approve plan review')
  })

  it('marks approval as done when latest approval is approved', () => {
    const steps = deriveStepStatuses({
      approval: { approval_status: 'approved', approved_by: 'alice' },
    })
    expect(steps.approval.status).toBe('done')
    expect(steps.approval.summary).toMatch(/alice/)
  })

  it('marks readyToTake as done when all upstream gates are done', () => {
    const steps = deriveStepStatuses({
      intelligence: { analysis_status: 'completed' },
      readiness: { readiness_status: 'ready_candidate' },
      approval: { approval_status: 'approved' },
    })
    expect(steps.readyToTake.status).toBe('done')
  })

  it('marks readyToTake as blocked when any upstream is blocked', () => {
    const steps = deriveStepStatuses({
      intelligence: { analysis_status: 'completed' },
      readiness: { readiness_status: 'blocked', blocking_reasons: ['x'] },
      approval: { approval_status: 'approved' },
    })
    expect(steps.readyToTake.status).toBe('blocked')
  })

  it('marks execution as done for post-execution ticket states', () => {
    expect(deriveStepStatuses({ ticket: { state: 'MERGED' } }).execution.status).toBe('done')
    expect(deriveStepStatuses({ ticket: { state: 'IMPLEMENTATION_APPROVED' } }).execution.status).toBe('done')
  })

  it('marks execution as blocked for conflict and *_FAILED states', () => {
    expect(deriveStepStatuses({ ticket: { state: 'CONFLICT_RESOLUTION_NEEDED' } }).execution.status).toBe('blocked')
    expect(deriveStepStatuses({ ticket: { state: 'CONFLICT_RESOLUTION_FAILED' } }).execution.status).toBe('blocked')
    expect(deriveStepStatuses({ ticket: { state: 'TEST_FAILED' } }).execution.status).toBe('blocked')
  })

  it('marks execution as current for active execution states', () => {
    expect(deriveStepStatuses({ ticket: { state: 'PLAN_APPROVED' } }).execution.status).toBe('current')
    expect(deriveStepStatuses({ ticket: { state: 'IMPLEMENTING' } }).execution.status).toBe('current')
  })
})

describe('deriveGlobalSummary', () => {
  it('returns BLOCKED / Human plan approval required when awaiting plan approval', () => {
    const steps = deriveStepStatuses({
      intelligence: { analysis_status: 'completed' },
      readiness: { readiness_status: 'ready_candidate' },
      approval: null,
    })
    const summary = deriveGlobalSummary(steps)
    expect(summary.status).toBe('BLOCKED')
    expect(summary.reason).toBe('Human plan approval required')
    expect(summary.nextAction).toBe('Approve plan review')
  })

  it('returns READY TO TAKE / All checks passed / Assign worker when all gates pass and no execution started', () => {
    const steps = deriveStepStatuses({
      intelligence: { analysis_status: 'completed' },
      readiness: { readiness_status: 'ready_candidate' },
      approval: { approval_status: 'approved' },
      ticket: { state: 'QUEUED' },
    })
    const summary = deriveGlobalSummary(steps)
    expect(summary.status).toBe('READY TO TAKE')
    expect(summary.reason).toBe('All checks passed')
    expect(summary.nextAction).toBe('Assign worker')
  })

  it('returns BLOCKED with readiness reason when readiness is blocked', () => {
    const steps = deriveStepStatuses({
      intelligence: { analysis_status: 'completed' },
      readiness: { readiness_status: 'blocked', blocking_reasons: ['needs human input'] },
    })
    const summary = deriveGlobalSummary(steps)
    expect(summary.status).toBe('BLOCKED')
    expect(summary.reason).toBe('needs human input')
  })

  it('returns IN PROGRESS when execution is current', () => {
    const steps = deriveStepStatuses({
      intelligence: { analysis_status: 'completed' },
      readiness: { readiness_status: 'ready_candidate' },
      approval: { approval_status: 'approved' },
      ticket: { state: 'PLAN_APPROVED' },
    })
    const summary = deriveGlobalSummary(steps)
    expect(summary.status).toBe('IN PROGRESS')
  })

  it('eligibilityToGlobalSummary returns null when payload is missing', () => {
    expect(eligibilityToGlobalSummary(null)).toBeNull()
    expect(eligibilityToGlobalSummary(undefined)).toBeNull()
  })

  it('eligibilityToGlobalSummary maps READY_TO_TAKE to the UI badge label', () => {
    const out = eligibilityToGlobalSummary({
      status: 'READY_TO_TAKE',
      reason: 'All eligibility checks passed.',
      next_action: 'Ticket can be taken by a worker',
    })
    expect(out).toEqual({
      status: 'READY TO TAKE',
      reason: 'All eligibility checks passed.',
      nextAction: 'Ticket can be taken by a worker',
    })
  })

  it('eligibilityToGlobalSummary maps WAITING_HUMAN_ACTION / DEPENDENCY_BLOCKED labels', () => {
    expect(eligibilityToGlobalSummary({
      status: 'WAITING_HUMAN_ACTION',
      reason: 'Human plan approval required',
      next_action: 'Approve plan review',
    }).status).toBe('WAITING HUMAN ACTION')

    expect(eligibilityToGlobalSummary({
      status: 'DEPENDENCY_BLOCKED',
      reason: 'Dependency T001 not merged',
      next_action: 'Wait for T001 to be merged',
    }).status).toBe('DEPENDENCY BLOCKED')
  })

  it('eligibilityToGlobalSummary falls back to UNKNOWN for unrecognised status', () => {
    expect(eligibilityToGlobalSummary({ status: 'NOT_A_REAL_STATUS' }).status).toBe('UNKNOWN')
  })

  it('returns COMPLETE when execution is done', () => {
    const steps = deriveStepStatuses({
      intelligence: { analysis_status: 'completed' },
      readiness: { readiness_status: 'ready_candidate' },
      approval: { approval_status: 'approved' },
      ticket: { state: 'MERGED' },
    })
    const summary = deriveGlobalSummary(steps)
    expect(summary.status).toBe('COMPLETE')
  })
})
