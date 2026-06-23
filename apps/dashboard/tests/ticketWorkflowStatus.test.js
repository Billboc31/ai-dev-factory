import { describe, expect, it } from 'vitest'
import {
  STEP_KEYS,
  deriveGlobalSummary,
  deriveStepStatuses,
} from '../src/lib/ticketWorkflowStatus'

describe('deriveStepStatuses', () => {
  it('returns all pending when nothing has started', () => {
    const steps = deriveStepStatuses({})
    expect(Object.keys(steps).sort()).toEqual([...STEP_KEYS].sort())
    expect(steps.intelligence.status).toBe('pending')
    expect(steps.readiness.status).toBe('pending')
    expect(steps.rules.status).toBe('pending')
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
        blocking_reasons: ['missing approval', 'stale context'],
      },
    })
    expect(steps.readiness.status).toBe('blocked')
    expect(steps.readiness.blockingReason).toBe('missing approval')
  })

  it('marks rules as blocked with the first failed-rule reason', () => {
    const steps = deriveStepStatuses({
      ruleEvaluation: {
        eligibility_status: 'blocked',
        failed_rules: [
          { rule_key: 'no-foo', reason: 'foo is forbidden' },
          { rule_key: 'no-bar', reason: 'bar is forbidden' },
        ],
      },
    })
    expect(steps.rules.status).toBe('blocked')
    expect(steps.rules.blockingReason).toBe('foo is forbidden')
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
      ruleEvaluation: { eligibility_status: 'eligible' },
      approval: { approval_status: 'approved' },
    })
    expect(steps.readyToTake.status).toBe('done')
  })

  it('marks readyToTake as blocked when any upstream is blocked', () => {
    const steps = deriveStepStatuses({
      intelligence: { analysis_status: 'completed' },
      readiness: { readiness_status: 'blocked', blocking_reasons: ['x'] },
      ruleEvaluation: { eligibility_status: 'eligible' },
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
      ruleEvaluation: { eligibility_status: 'eligible' },
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
      ruleEvaluation: { eligibility_status: 'eligible' },
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
      ruleEvaluation: { eligibility_status: 'eligible' },
      approval: { approval_status: 'approved' },
      ticket: { state: 'PLAN_APPROVED' },
    })
    const summary = deriveGlobalSummary(steps)
    expect(summary.status).toBe('IN PROGRESS')
  })

  it('returns COMPLETE when execution is done', () => {
    const steps = deriveStepStatuses({
      intelligence: { analysis_status: 'completed' },
      readiness: { readiness_status: 'ready_candidate' },
      ruleEvaluation: { eligibility_status: 'eligible' },
      approval: { approval_status: 'approved' },
      ticket: { state: 'MERGED' },
    })
    const summary = deriveGlobalSummary(steps)
    expect(summary.status).toBe('COMPLETE')
  })
})
