import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import TicketDetailPage from '../src/pages/TicketDetailPage'
import * as ticketsApi from '../src/api/tickets'

vi.mock('../src/api/tickets')

const MOCK_TICKET = {
  ticket_id: 'T028',
  state: 'PLAN_APPROVED',
  branch: 'ticket/T028-control-api',
  updated_at: '2026-05-15T09:00:00Z'
}

function renderPage(id = 'T028') {
  return render(
    <MemoryRouter initialEntries={[`/tickets/${id}`]}>
      <Routes>
        <Route path="/tickets/:id" element={<TicketDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('TicketDetailPage', () => {
  beforeEach(() => {
    ticketsApi.getTicket.mockResolvedValue({ data: MOCK_TICKET })
  })

  it('displays the ticket ID and state', async () => {
    renderPage()
    expect(await screen.findByText('T028')).toBeInTheDocument()
    expect(await screen.findByText('PLAN_APPROVED')).toBeInTheDocument()
  })

  it('renders workflow action buttons', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: /run next/i })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /approve plan/i })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /request plan fix/i })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /approve implementation/i })).toBeInTheDocument()
  })

  it('renders git action buttons', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: /commit/i })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /push/i })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /checkpoint/i })).toBeInTheDocument()
  })

  it('shows error banner when the API fails', async () => {
    ticketsApi.getTicket.mockRejectedValue({ message: 'Not found' })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Not found')
  })

  it('calls approvePlan API when button is clicked', async () => {
    ticketsApi.approvePlan.mockResolvedValue({ data: { ok: true, message: 'Plan approved' } })
    renderPage()

    const btn = await screen.findByRole('button', { name: /approve plan/i })
    await userEvent.click(btn)

    expect(ticketsApi.approvePlan).toHaveBeenCalledWith('T028')
    expect(await screen.findByText('Plan approved')).toBeInTheDocument()
  })

  it('shows error message when action API fails', async () => {
    ticketsApi.runNextStep.mockRejectedValue({ response: { data: { detail: 'Step failed' } } })
    renderPage()

    const btn = await screen.findByRole('button', { name: /run next/i })
    await userEvent.click(btn)

    expect(await screen.findByText('Step failed')).toBeInTheDocument()
  })

  it('loads and displays artifacts when artifacts tab is clicked', async () => {
    ticketsApi.getTicketArtifacts.mockResolvedValue({ data: ['runs/T028/plan.md', 'runs/T028/state.json'] })
    renderPage()
    const artifactsTab = await screen.findByRole('button', { name: /artifacts/i })
    await userEvent.click(artifactsTab)
    expect(ticketsApi.getTicketArtifacts).toHaveBeenCalledWith('T028')
    expect(await screen.findByText(/plan\.md/)).toBeInTheDocument()
  })

  it('has a back link to the tickets list', async () => {
    renderPage()
    const link = await screen.findByRole('link', { name: /back to tickets/i })
    expect(link).toHaveAttribute('href', '/')
  })
})
