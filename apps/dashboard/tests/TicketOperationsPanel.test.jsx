import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TicketOperationsPanel from '../src/components/TicketOperationsPanel'
import * as ticketsApi from '../src/api/tickets'

vi.mock('../src/api/tickets')

const TICKET_ID = 'T204'
const PROJECT_ID = 'proj-a'

const ALL_OPERATIONS = {
  ticket_id: TICKET_ID,
  operations: [
    {
      operation_key: 'rerun_diagnostics',
      label: 'Re-run diagnostics',
      group: 'advisory',
      safety_level: 'low',
      enabled: true,
      disabled_reason: null,
      requires_reason: false,
      requires_typed_ticket_id: false,
      requires_double_confirmation: false,
    },
    {
      operation_key: 'approve_execution',
      label: 'Approve execution',
      group: 'approval',
      safety_level: 'medium',
      enabled: true,
      disabled_reason: null,
      requires_reason: false,
      requires_typed_ticket_id: false,
      requires_double_confirmation: false,
    },
    {
      operation_key: 'reset_to_planning',
      label: 'Reset ticket to planning',
      group: 'recovery',
      safety_level: 'high',
      enabled: true,
      disabled_reason: null,
      requires_reason: true,
      requires_typed_ticket_id: true,
      requires_double_confirmation: false,
    },
    {
      operation_key: 'delete_worktree',
      label: 'Delete ticket worktree',
      group: 'dangerous',
      safety_level: 'destructive',
      enabled: false,
      disabled_reason: 'Worktree does not exist.',
      requires_reason: false,
      requires_typed_ticket_id: true,
      requires_double_confirmation: true,
    },
  ],
}

const DIAGNOSTICS_WITH_RECOMMEND = {
  ticket_id: TICKET_ID,
  diagnostic_status: 'completed',
  is_stuck: true,
  severity: 'warning',
  summary: 'Waiting for approval',
  current_state: 'PLAN_APPROVED',
  last_known_step: 'planner',
  last_error: null,
  checks: [],
  recommended_actions: [
    { action_key: 'approve_execution', label: 'Approve execution', risk: 'low', reason: 'pending' },
  ],
  generated_at: '2026-06-22T12:00:00Z',
}

function renderPanel() {
  return render(<TicketOperationsPanel ticketId={TICKET_ID} projectId={PROJECT_ID} />)
}

describe('TicketOperationsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all four operation groups', async () => {
    ticketsApi.listTicketOperations.mockResolvedValue({ data: ALL_OPERATIONS })
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: null })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText('Advisory re-runs')).toBeInTheDocument()
      expect(screen.getByText('Approval actions')).toBeInTheDocument()
      expect(screen.getByText('Recovery actions')).toBeInTheDocument()
      expect(screen.getByText('Dangerous actions')).toBeInTheDocument()
    })
  })

  it('shows disabled reason for disabled operations', async () => {
    ticketsApi.listTicketOperations.mockResolvedValue({ data: ALL_OPERATIONS })
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: null })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Worktree does not exist/)).toBeInTheDocument()
    })
  })

  it('high safety: refuses submit when typed ticket id mismatches', async () => {
    const user = userEvent.setup()
    ticketsApi.listTicketOperations.mockResolvedValue({ data: ALL_OPERATIONS })
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: null })
    renderPanel()
    await waitFor(() => screen.getByRole('button', { name: /Reset ticket to planning/ }))
    await user.click(screen.getByRole('button', { name: /Reset ticket to planning/ }))
    // Modal opens.
    await waitFor(() => screen.getByRole('dialog'))
    // Confirm disabled until reason + typed id provided.
    const confirmBtn = screen.getByRole('button', { name: /Confirm$/ })
    expect(confirmBtn).toBeDisabled()
    // Provide reason but a wrong typed id.
    const reasonInput = screen.getByPlaceholderText(/Reason \(required\)/)
    await user.type(reasonInput, 'stale plan')
    const typedInput = screen.getByDisplayValue('')
    await user.type(typedInput, 'WRONG')
    expect(confirmBtn).toBeDisabled()
  })

  it('low safety: clicking triggers immediate POST', async () => {
    const user = userEvent.setup()
    ticketsApi.listTicketOperations.mockResolvedValue({ data: ALL_OPERATIONS })
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: null })
    ticketsApi.executeTicketOperation.mockResolvedValue({
      data: {
        ticket_id: TICKET_ID,
        operation_key: 'rerun_diagnostics',
        status: 'completed',
        message: 'Diagnostics re-run completed.',
        details: {},
      },
    })
    renderPanel()
    await waitFor(() => screen.getByRole('button', { name: /Re-run diagnostics/ }))
    await user.click(screen.getByRole('button', { name: /Re-run diagnostics/ }))
    await waitFor(() => {
      expect(ticketsApi.executeTicketOperation).toHaveBeenCalledWith(
        TICKET_ID, PROJECT_ID, 'rerun_diagnostics',
        expect.objectContaining({ confirm: true }),
      )
      expect(screen.getByText(/Diagnostics re-run completed/)).toBeInTheDocument()
    })
  })

  it('renders Recommended by diagnostics chip for matching action', async () => {
    ticketsApi.listTicketOperations.mockResolvedValue({ data: ALL_OPERATIONS })
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: DIAGNOSTICS_WITH_RECOMMEND })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Recommended by diagnostics/)).toBeInTheDocument()
    })
  })

  it('surfaces API error in result message', async () => {
    const user = userEvent.setup()
    ticketsApi.listTicketOperations.mockResolvedValue({ data: ALL_OPERATIONS })
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: null })
    ticketsApi.executeTicketOperation.mockRejectedValue({
      response: { data: { detail: 'something went wrong' }, status: 400 },
    })
    renderPanel()
    await waitFor(() => screen.getByRole('button', { name: /Re-run diagnostics/ }))
    await user.click(screen.getByRole('button', { name: /Re-run diagnostics/ }))
    await waitFor(() => {
      expect(screen.getByText(/something went wrong/)).toBeInTheDocument()
    })
  })
})
