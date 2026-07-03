import { render, screen, act, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import TicketDetailPage from '../src/pages/TicketDetailPage'
import * as ticketsApi from '../src/api/tickets'
import usePolling from '../src/hooks/usePolling'

vi.mock('../src/api/tickets')
vi.mock('../src/hooks/usePolling')

const MOCK_TICKET = {
  ticket_id: 'T028',
  state: 'PLAN_APPROVED',
  branch: 'ticket/T028-control-api',
  updated_at: '2026-05-15T09:00:00Z'
}

const MOCK_STATE = { ticket_id: 'T028', state: 'PLAN_APPROVED', step: 'coder' }

const MOCK_TIMELINE = {
  ticket_id: 'T028',
  current_state: 'PLAN_APPROVED',
  current_agent: 'coder',
  human_gate: false,
  last_event: null,
  steps: [
    { id: 'issue_intake', label: 'Issue intake', status: 'done', agent: null },
    { id: 'plan', label: 'Plan', status: 'done', agent: null },
    { id: 'plan_review', label: 'Plan review', status: 'done', agent: null },
    { id: 'implementation', label: 'Implementation', status: 'running', agent: 'coder' },
    { id: 'implementation_review', label: 'Implementation review', status: 'pending', agent: null },
    { id: 'fix_loop', label: 'Fix loop', status: 'pending', agent: null },
    { id: 'tests', label: 'Tests', status: 'pending', agent: null },
  ]
}

function renderPage(id = 'T028', projectId = 'test-project') {
  return render(
    <MemoryRouter initialEntries={[`/projects/${projectId}/tickets/${id}`]}>
      <Routes>
        <Route path="/projects/:projectId/tickets/:id" element={<TicketDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('TicketDetailPage — runtime state change', () => {
  // The page's first `usePolling` invocation is the ticket fetch (called on
  // initial render, before any per-panel poller mounts). Capture only that
  // first registration so subsequent panel registrations don't clobber it.
  let simulatePoll

  beforeEach(() => {
    vi.clearAllMocks()
    simulatePoll = undefined
    usePolling.mockImplementation((callback) => {
      if (simulatePoll === undefined) {
        simulatePoll = callback
      }
    })
    ticketsApi.getTicketState.mockResolvedValue({ data: MOCK_STATE })
    ticketsApi.getTicketLogs.mockResolvedValue({ data: 'line 1\nline 2' })
    ticketsApi.getTicketTimeline.mockResolvedValue({ data: MOCK_TIMELINE })
    ticketsApi.getTicketPlan.mockResolvedValue({ data: '# Plan content' })
    // The page-level workflow fetch and each step's expanded panel call these
    // endpoints; provide empty defaults so panels don't crash on render.
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: null })
    ticketsApi.getTicketReadiness.mockResolvedValue({ data: null })
    ticketsApi.getTicketApprovals.mockResolvedValue({ data: { approvals: [] } })
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: null })
    ticketsApi.listTicketOperations.mockResolvedValue({ data: { operations: [] } })
  })

  it('invalidates tab content when ticket state changes', async () => {
    ticketsApi.getTicket
      .mockResolvedValueOnce({ data: { ...MOCK_TICKET, state: 'PLAN_APPROVED' } })
      .mockResolvedValueOnce({ data: { ...MOCK_TICKET, state: 'CODER_RUNNING' } })

    renderPage()

    // First poll — loads ticket and timeline tab content
    await act(async () => { simulatePoll() })
    await waitFor(() => expect(ticketsApi.getTicketTimeline).toHaveBeenCalled())
    const callsBefore = ticketsApi.getTicketTimeline.mock.calls.length

    // Second poll — state changes
    await act(async () => { simulatePoll() })

    // State changed → tabContent cleared → timeline re-fetched
    expect(await screen.findByText('CODER_RUNNING')).toBeInTheDocument()
    await waitFor(() => {
      expect(ticketsApi.getTicketTimeline.mock.calls.length).toBeGreaterThan(callsBefore)
    })
  })

  it('preserves tab content when ticket state is unchanged', async () => {
    ticketsApi.getTicket.mockResolvedValue({ data: MOCK_TICKET })

    renderPage()

    // First poll — loads ticket and timeline tab
    await act(async () => { simulatePoll() })
    expect(await screen.findByText('PLAN_APPROVED')).toBeInTheDocument()

    // Switch to plan tab (a stable tab, unlike logs/timeline/overview)
    await userEvent.click(screen.getByRole('button', { name: /^plan$/i }))
    await waitFor(() => expect(ticketsApi.getTicketPlan).toHaveBeenCalled())
    const callsBefore = ticketsApi.getTicketPlan.mock.calls.length

    // Second poll — same state, on plan tab
    await act(async () => { simulatePoll() })
    await waitFor(() => expect(ticketsApi.getTicket).toHaveBeenCalledTimes(2))
    await act(async () => {}) // flush any trailing effects

    // tabContent preserved — plan not re-fetched
    expect(ticketsApi.getTicketPlan.mock.calls.length).toBe(callsBefore)
  })

  it('renders the workflow timeline global summary block', async () => {
    ticketsApi.getTicket.mockResolvedValue({ data: MOCK_TICKET })

    renderPage()

    await act(async () => { simulatePoll() })
    expect(await screen.findByTestId('ticket-workflow-global-summary')).toBeInTheDocument()
  })

  it('re-fetches logs on each poll when logs tab is active', async () => {
    ticketsApi.getTicket.mockResolvedValue({ data: MOCK_TICKET })

    renderPage()

    // First poll — loads ticket
    await act(async () => { simulatePoll() })
    expect(await screen.findByText('PLAN_APPROVED')).toBeInTheDocument()

    // Switch to logs tab and wait for initial load
    await userEvent.click(screen.getByRole('button', { name: /logs/i }))
    await waitFor(() => expect(ticketsApi.getTicketLogs).toHaveBeenCalled())
    const callsBefore = ticketsApi.getTicketLogs.mock.calls.length

    // Second poll — same state, logs tab active
    await act(async () => { simulatePoll() })

    // Logs re-fetched despite unchanged ticket state
    await waitFor(() => {
      expect(ticketsApi.getTicketLogs.mock.calls.length).toBeGreaterThan(callsBefore)
    })
  })

})

describe('TicketDetailPage — plan approval badge', () => {
  // Capture the first two distinct polling callbacks: the page mounts a poller
  // for the ticket fetch (1st call) and one for the workflow data fetch that
  // populates `approvals` (2nd call).
  let firstPoll
  let secondPoll

  beforeEach(() => {
    vi.clearAllMocks()
    firstPoll = undefined
    secondPoll = undefined
    usePolling.mockImplementation((callback) => {
      if (firstPoll === undefined) {
        firstPoll = callback
      } else if (secondPoll === undefined && callback !== firstPoll) {
        secondPoll = callback
      }
    })
    ticketsApi.getTicketState.mockResolvedValue({ data: MOCK_STATE })
    ticketsApi.getTicketLogs.mockResolvedValue({ data: '' })
    ticketsApi.getTicketTimeline.mockResolvedValue({ data: MOCK_TIMELINE })
    ticketsApi.getTicketPlan.mockResolvedValue({ data: '' })
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: null })
    ticketsApi.getTicketReadiness.mockResolvedValue({ data: null })
    ticketsApi.getTicketDiagnostics.mockResolvedValue({ data: null })
    ticketsApi.listTicketOperations.mockResolvedValue({ data: { operations: [] } })
    ticketsApi.getTicketEligibility.mockResolvedValue({ data: null })
    ticketsApi.getTicket.mockResolvedValue({ data: MOCK_TICKET })
  })

  const pollAll = async () => {
    await act(async () => { firstPoll && firstPoll() })
    await act(async () => { secondPoll && secondPoll() })
  }

  it('renders an Auto-approved badge and hides plan approve buttons when the plan was SYSTEM-approved', async () => {
    ticketsApi.getTicketApprovals.mockResolvedValue({
      data: {
        approvals: [
          {
            id: 1,
            approval_type: 'plan',
            approval_status: 'approved',
            approved_by: 'SYSTEM',
            approval_comment: 'PROJECT_SETTING',
          },
        ],
      },
    })

    renderPage()
    await pollAll()

    await waitFor(() => {
      expect(screen.getByTestId('plan-auto-approved-badge')).toBeInTheDocument()
    })
    expect(screen.queryByRole('button', { name: /Approve Plan$/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /Request Plan Fix/i })).toBeNull()
    // Implementation approval buttons remain visible.
    expect(screen.getByRole('button', { name: /Approve Implementation/i })).toBeInTheDocument()
  })

  it('keeps manual plan approve buttons when the latest plan approval is human', async () => {
    ticketsApi.getTicketApprovals.mockResolvedValue({
      data: {
        approvals: [
          {
            id: 1,
            approval_type: 'plan',
            approval_status: 'approved',
            approved_by: 'pierre',
            approval_comment: 'looks good',
          },
        ],
      },
    })

    renderPage()
    await pollAll()

    await waitFor(() => {
      expect(screen.getByText('PLAN_APPROVED')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('plan-auto-approved-badge')).toBeNull()
    expect(screen.getByRole('button', { name: /Approve Plan$/i })).toBeInTheDocument()
  })
})
