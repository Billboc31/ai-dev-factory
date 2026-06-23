import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TicketWorkflowTimeline from '../src/components/TicketWorkflowTimeline'
import {
  STEP_KEYS,
  deriveGlobalSummary,
  deriveStepStatuses,
} from '../src/lib/ticketWorkflowStatus'

const APPROVAL_PENDING_FIXTURE = {
  intelligence: { analysis_status: 'completed', difficulty_score: 4, risk_score: 3 },
  readiness: { readiness_status: 'ready_candidate' },
  ruleEvaluation: { eligibility_status: 'eligible' },
  approval: null,
}

const ALL_DONE_FIXTURE = {
  intelligence: { analysis_status: 'completed', difficulty_score: 2, risk_score: 1 },
  readiness: { readiness_status: 'ready_candidate' },
  ruleEvaluation: { eligibility_status: 'eligible' },
  approval: { approval_status: 'approved', approved_by: 'alice' },
  ticket: { state: 'QUEUED' },
}

function renderTimeline(fixture, content = {}) {
  const steps = deriveStepStatuses(fixture)
  const summary = deriveGlobalSummary(steps)
  return render(
    <TicketWorkflowTimeline
      stepStatuses={steps}
      globalSummary={summary}
      stepContent={content}
    />
  )
}

describe('TicketWorkflowTimeline', () => {
  it('renders all six steps in workflow order', () => {
    renderTimeline(APPROVAL_PENDING_FIXTURE)
    for (const key of STEP_KEYS) {
      expect(screen.getByTestId(`workflow-step-${key}`)).toBeInTheDocument()
    }
    // Verify ordering in the DOM
    const rendered = STEP_KEYS.map(k => screen.getByTestId(`workflow-step-${k}`))
    for (let i = 1; i < rendered.length; i++) {
      // rendered[i] should appear after rendered[i-1] in document order
      // eslint-disable-next-line no-bitwise
      expect(rendered[i - 1].compareDocumentPosition(rendered[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    }
  })

  it('shows the blocked-by-approval global summary fixture', () => {
    renderTimeline(APPROVAL_PENDING_FIXTURE)
    const block = screen.getByTestId('ticket-workflow-global-summary')
    expect(block).toHaveTextContent('BLOCKED')
    expect(block).toHaveTextContent('Human plan approval required')
    expect(block).toHaveTextContent('Approve plan review')
  })

  it('shows the READY TO TAKE summary when all gates pass', () => {
    renderTimeline(ALL_DONE_FIXTURE)
    const block = screen.getByTestId('ticket-workflow-global-summary')
    expect(block).toHaveTextContent('READY TO TAKE')
    expect(block).toHaveTextContent('All checks passed')
    expect(block).toHaveTextContent('Assign worker')
  })

  it('auto-opens the first current/blocked step (Approval here)', () => {
    renderTimeline(APPROVAL_PENDING_FIXTURE, {
      approval: <p>APPROVAL_PANEL_CONTENT</p>,
    })
    const approvalStep = screen.getByTestId('workflow-step-approval')
    expect(approvalStep.open).toBe(true)
    expect(screen.getByText('APPROVAL_PANEL_CONTENT')).toBeInTheDocument()
  })

  it('expanding a collapsed step reveals its children', async () => {
    const user = userEvent.setup()
    renderTimeline(ALL_DONE_FIXTURE, {
      intelligence: <p>INTEL_DETAILS</p>,
    })
    const intelStep = screen.getByTestId('workflow-step-intelligence')
    expect(intelStep.open).toBe(false)
    const summaryEl = intelStep.querySelector('summary')
    await user.click(summaryEl)
    expect(intelStep.open).toBe(true)
    expect(screen.getByText('INTEL_DETAILS')).toBeInTheDocument()
  })

  it('shows the blocking reason on the corresponding step', () => {
    const fixture = {
      ...APPROVAL_PENDING_FIXTURE,
      readiness: {
        readiness_status: 'blocked',
        blocking_reasons: ['Missing approval'],
      },
    }
    renderTimeline(fixture)
    const readinessStep = screen.getByTestId('workflow-step-readiness')
    expect(readinessStep).toHaveTextContent(/Missing approval/)
  })
})
