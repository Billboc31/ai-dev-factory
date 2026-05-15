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

function renderPage(id = 'T028') {
  return render(
    <MemoryRouter initialEntries={[`/tickets/${id}`]}>
      <Routes>
        <Route path="/tickets/:id" element={<TicketDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('TicketDetailPage — runtime state change', () => {
  let simulatePoll

  beforeEach(() => {
    vi.clearAllMocks()
    // Capture the polling callback without calling it — avoids calling it on every re-render
    usePolling.mockImplementation((callback) => { simulatePoll = callback })
    ticketsApi.getTicketState.mockResolvedValue({ data: MOCK_STATE })
    ticketsApi.getTicketLogs.mockResolvedValue({ data: 'line 1\nline 2' })
  })

  it('invalidates tab content when ticket state changes', async () => {
    ticketsApi.getTicket
      .mockResolvedValueOnce({ data: { ...MOCK_TICKET, state: 'PLAN_APPROVED' } })
      .mockResolvedValueOnce({ data: { ...MOCK_TICKET, state: 'CODER_RUNNING' } })

    renderPage()

    // First poll — loads ticket and overview tab content
    await act(async () => { simulatePoll() })
    await waitFor(() => expect(ticketsApi.getTicketState).toHaveBeenCalled())
    const callsBefore = ticketsApi.getTicketState.mock.calls.length

    // Second poll — state changes
    await act(async () => { simulatePoll() })

    // State changed → tabContent cleared → overview re-fetched
    expect(await screen.findByText('CODER_RUNNING')).toBeInTheDocument()
    await waitFor(() => {
      expect(ticketsApi.getTicketState.mock.calls.length).toBeGreaterThan(callsBefore)
    })
  })

  it('preserves tab content when ticket state is unchanged', async () => {
    ticketsApi.getTicket.mockResolvedValue({ data: MOCK_TICKET })

    renderPage()

    // First poll
    await act(async () => { simulatePoll() })
    await waitFor(() => expect(ticketsApi.getTicketState).toHaveBeenCalled())
    const callsBefore = ticketsApi.getTicketState.mock.calls.length

    // Second poll — same state, not on logs tab
    await act(async () => { simulatePoll() })
    await waitFor(() => expect(ticketsApi.getTicket).toHaveBeenCalledTimes(2))
    await act(async () => {}) // flush any trailing effects

    // tabContent preserved — overview not re-fetched
    expect(ticketsApi.getTicketState.mock.calls.length).toBe(callsBefore)
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
