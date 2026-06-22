import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TicketRuleEvaluationPanel from '../src/components/TicketRuleEvaluationPanel'
import * as ticketsApi from '../src/api/tickets'

vi.mock('../src/api/tickets')

const TICKET_ID = 'T201'
const PROJECT_ID = 'proj-a'

const ELIGIBLE = {
  ticket_id: TICKET_ID,
  project_id: PROJECT_ID,
  eligibility_status: 'eligible',
  passed_rules: [
    { rule_key: 'require_human_approval', reason: 'ok' },
  ],
  failed_rules: [],
  warnings: [],
  evaluated_at: '2026-06-22T10:00:00Z',
}

const BLOCKED = {
  ticket_id: TICKET_ID,
  project_id: PROJECT_ID,
  eligibility_status: 'blocked',
  passed_rules: [],
  failed_rules: [
    { rule_key: 'require_human_approval', reason: 'Human execution approval is missing.' },
    { rule_key: 'max_difficulty', reason: 'Difficulty score 9 exceeds limit 5.' },
  ],
  warnings: [
    { rule_key: 'max_estimated_cost_usd', message: 'Estimated AI cost is unknown.' },
  ],
  evaluated_at: '2026-06-22T10:05:00Z',
}

function renderPanel() {
  return render(<TicketRuleEvaluationPanel ticketId={TICKET_ID} projectId={PROJECT_ID} />)
}

describe('TicketRuleEvaluationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders eligible badge for eligible status', async () => {
    ticketsApi.getTicketRuleEvaluation.mockResolvedValue({ data: ELIGIBLE })
    renderPanel()
    await waitFor(() => {
      const badge = screen.getByText('eligible')
      expect(badge).toBeInTheDocument()
      expect(badge.className).toMatch(/green/)
    })
  })

  it('renders blocked badge for blocked status', async () => {
    ticketsApi.getTicketRuleEvaluation.mockResolvedValue({ data: BLOCKED })
    renderPanel()
    await waitFor(() => {
      const badge = screen.getByText('blocked')
      expect(badge).toBeInTheDocument()
      expect(badge.className).toMatch(/red/)
    })
  })

  it('renders failed rules with their reasons', async () => {
    ticketsApi.getTicketRuleEvaluation.mockResolvedValue({ data: BLOCKED })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Failed rules/)).toBeInTheDocument()
      expect(screen.getByText(/require_human_approval/)).toBeInTheDocument()
      expect(screen.getByText(/Human execution approval is missing/)).toBeInTheDocument()
      expect(screen.getByText(/Difficulty score 9 exceeds limit 5/)).toBeInTheDocument()
    })
  })

  it('renders warnings list', async () => {
    ticketsApi.getTicketRuleEvaluation.mockResolvedValue({ data: BLOCKED })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Warnings/)).toBeInTheDocument()
      expect(screen.getByText(/Estimated AI cost is unknown/)).toBeInTheDocument()
    })
  })

  it('shows no-evaluation hint on 404', async () => {
    ticketsApi.getTicketRuleEvaluation.mockRejectedValue({ response: { status: 404 } })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/No rule evaluation yet/)).toBeInTheDocument()
    })
  })

  it('renders Evaluate when no evaluation yet', async () => {
    ticketsApi.getTicketRuleEvaluation.mockRejectedValue({ response: { status: 404 } })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Evaluate' })).toBeInTheDocument()
    })
  })

  it('renders Re-evaluate when evaluation present', async () => {
    ticketsApi.getTicketRuleEvaluation.mockResolvedValue({ data: ELIGIBLE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Re-evaluate' })).toBeInTheDocument()
    })
  })

  it('clicking Re-evaluate calls the POST endpoint and re-fetches GET', async () => {
    const user = userEvent.setup()
    ticketsApi.getTicketRuleEvaluation
      .mockResolvedValueOnce({ data: ELIGIBLE })
      .mockResolvedValue({
        data: { ...ELIGIBLE, evaluated_at: '2026-06-22T11:00:00Z' },
      })
    ticketsApi.postEvaluateTicketRules.mockResolvedValue({
      data: { status: 'scheduled', ticket_id: TICKET_ID },
    })

    renderPanel()
    await waitFor(() => screen.getByRole('button', { name: 'Re-evaluate' }))
    await user.click(screen.getByRole('button', { name: 'Re-evaluate' }))

    expect(ticketsApi.postEvaluateTicketRules).toHaveBeenCalledWith(TICKET_ID, PROJECT_ID)
    await waitFor(
      () => expect(ticketsApi.getTicketRuleEvaluation).toHaveBeenCalledTimes(2),
      { timeout: 4000 },
    )
  })

  it('shows formatted evaluated_at', async () => {
    ticketsApi.getTicketRuleEvaluation.mockResolvedValue({ data: ELIGIBLE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Last evaluated:/)).toBeInTheDocument()
    })
  })
})
