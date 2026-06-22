import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TicketDiagnosticsPanel from '../src/components/TicketDiagnosticsPanel'
import * as ticketsApi from '../src/api/tickets'

vi.mock('../src/api/tickets')

const TICKET_ID = 'T203'
const PROJECT_ID = 'proj-a'

const HEALTHY = {
  ticket_id: TICKET_ID,
  diagnostic_status: 'completed',
  is_stuck: false,
  severity: 'info',
  summary: 'Ticket has no detected blockers.',
  current_state: 'DONE',
  last_known_step: 'merge',
  last_error: null,
  checks: [
    { key: 'ticket_existence', status: 'passed', message: 'ok', details: {} },
  ],
  recommended_actions: [],
  generated_at: '2026-06-22T12:00:00Z',
}

const STUCK = {
  ticket_id: TICKET_ID,
  diagnostic_status: 'completed',
  is_stuck: true,
  severity: 'warning',
  summary: 'Ticket is waiting for human approval.',
  current_state: 'WAITING_APPROVAL',
  last_known_step: 'plan_review',
  last_error: null,
  checks: [
    { key: 'ticket_existence', status: 'passed', message: 'ok', details: {} },
    { key: 'approval', status: 'failed', message: 'Execution approval is missing.', details: {} },
  ],
  recommended_actions: [
    { action_key: 'approve_execution', label: 'Approve execution', risk: 'low', reason: 'missing approval' },
    { action_key: 'reject_execution', label: 'Reject execution', risk: 'medium', reason: 'missing approval' },
  ],
  generated_at: '2026-06-22T12:00:00Z',
}

function renderPanel() {
  return render(<TicketDiagnosticsPanel ticketId={TICKET_ID} projectId={PROJECT_ID} />)
}

describe('TicketDiagnosticsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders healthy state with HEALTHY badge', async () => {
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: HEALTHY })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText('HEALTHY')).toBeInTheDocument()
      expect(screen.getByText(/no detected blockers/i)).toBeInTheDocument()
    })
  })

  it('renders stuck state with STUCK badge and recommended actions', async () => {
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: STUCK })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText('STUCK')).toBeInTheDocument()
      expect(screen.getByText(/waiting for human approval/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Approve execution/ })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Reject execution/ })).toBeInTheDocument()
    })
  })

  it('recommended action buttons are disabled', async () => {
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: STUCK })
    renderPanel()
    await waitFor(() => {
      const approveBtn = screen.getByRole('button', { name: /Approve execution/ })
      expect(approveBtn).toBeDisabled()
      // "Action not wired yet" badge present.
      expect(screen.getAllByText(/Action not wired yet/).length).toBeGreaterThan(0)
    })
  })

  it('shows empty state with Run diagnostics button on 404', async () => {
    ticketsApi.getTicketDiagnostics.mockRejectedValue({ response: { status: 404 } })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/No diagnostic yet/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Run diagnostics/i })).toBeInTheDocument()
    })
  })

  it('Run diagnostics triggers POST then re-fetches GET', async () => {
    const user = userEvent.setup()
    ticketsApi.getTicketDiagnostics
      .mockRejectedValueOnce({ response: { status: 404 } })
      .mockResolvedValue({ data: HEALTHY })
    ticketsApi.runTicketDiagnostics.mockResolvedValue({ data: HEALTHY })

    renderPanel()
    await waitFor(() => screen.getByRole('button', { name: /Run diagnostics/i }))
    await user.click(screen.getByRole('button', { name: /Run diagnostics/i }))

    await waitFor(() => {
      expect(ticketsApi.runTicketDiagnostics).toHaveBeenCalledWith(TICKET_ID, PROJECT_ID)
    })
    // Re-fetch after POST.
    await waitFor(() => {
      expect(ticketsApi.getTicketDiagnostics).toHaveBeenCalledTimes(2)
    })
  })

  it('renders generated_at date', async () => {
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: HEALTHY })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Generated:/)).toBeInTheDocument()
    })
  })
})
