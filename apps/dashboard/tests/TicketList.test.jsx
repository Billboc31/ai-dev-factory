import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TicketsPage from '../src/pages/TicketsPage'
import * as ticketsApi from '../src/api/tickets'

vi.mock('../src/api/tickets')

const MOCK_TICKETS = [
  { ticket_id: 'T028', state: 'TEST_COMPLETE', branch: 'ticket/T028-control-api', updated_at: '2026-05-15T09:00:00Z' },
  { ticket_id: 'T029', state: 'PLAN_APPROVED', branch: 'ticket/T029-dashboard', updated_at: '2026-05-15T10:00:00Z' }
]

function renderPage() {
  return render(
    <MemoryRouter>
      <TicketsPage />
    </MemoryRouter>
  )
}

describe('TicketsPage', () => {
  it('renders the page heading', async () => {
    ticketsApi.listTickets.mockResolvedValue({ data: [] })
    renderPage()
    expect(await screen.findByRole('heading', { name: /tickets/i })).toBeInTheDocument()
  })

  it('displays tickets returned by the API', async () => {
    ticketsApi.listTickets.mockResolvedValue({ data: MOCK_TICKETS })
    renderPage()

    expect(await screen.findByText('T028')).toBeInTheDocument()
    expect(await screen.findByText('TEST_COMPLETE')).toBeInTheDocument()
    expect(await screen.findByText('T029')).toBeInTheDocument()
    expect(await screen.findByText('PLAN_APPROVED')).toBeInTheDocument()
  })

  it('shows an empty message when no tickets exist', async () => {
    ticketsApi.listTickets.mockResolvedValue({ data: [] })
    renderPage()
    expect(await screen.findByText(/no tickets found/i)).toBeInTheDocument()
  })

  it('shows error banner on API failure', async () => {
    ticketsApi.listTickets.mockRejectedValue({ message: 'Network Error' })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Network Error')
  })

  it('links each ticket to its detail page', async () => {
    ticketsApi.listTickets.mockResolvedValue({ data: MOCK_TICKETS })
    renderPage()

    const link = await screen.findByRole('link', { name: 'T028' })
    expect(link).toHaveAttribute('href', '/tickets/T028')
  })
})
