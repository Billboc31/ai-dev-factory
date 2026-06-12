import { useEffect } from 'react'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProjectTicketsPage from '../src/pages/ProjectTicketsPage'
import { columnForState, COLUMN_DEFS } from '../src/lib/ticketColumns'
import * as projectsApi from '../src/api/projects'
import * as ticketsApi from '../src/api/tickets'

// Mock usePolling to call the callback once on mount (like the real hook does),
// not on every render (which would cause an infinite re-render loop in tests).
vi.mock('../src/hooks/usePolling', () => ({
  default: (callback) => {
    useEffect(() => { callback() }, []) // eslint-disable-line react-hooks/exhaustive-deps
  },
}))
vi.mock('../src/api/projects')
vi.mock('../src/api/tickets')

const QUEUED_TICKET = { ticket_id: 'T001', state: 'QUEUED', branch: 'ticket/T001', issue_number: 10, updated_at: '2026-06-01T10:00:00Z', last_log: 'queued' }
const RUNNING_TICKET = { ticket_id: 'T002', state: 'IMPLEMENTING', branch: 'ticket/T002', issue_number: 20, updated_at: '2026-06-01T11:00:00Z', last_log: 'running' }
const WAITING_TICKET = { ticket_id: 'T003', state: 'PLAN_REVIEW_NEEDED', branch: 'ticket/T003', issue_number: 30, updated_at: '2026-06-01T12:00:00Z', last_log: 'waiting' }
const DONE_TICKET = { ticket_id: 'T004', state: 'COMPLETED', branch: 'ticket/T004', issue_number: 40, updated_at: '2026-06-01T13:00:00Z', last_log: 'done' }

beforeEach(() => {
  vi.clearAllMocks()
  projectsApi.getProject.mockResolvedValue({ data: { github_repo: 'org/repo' } })
  ticketsApi.listTickets.mockResolvedValue({ data: [] })
  ticketsApi.getTicketTimeline.mockResolvedValue({ data: { last_error: null } })
})

function renderBoard(tickets = []) {
  ticketsApi.listTickets.mockResolvedValue({ data: tickets })
  return render(
    <MemoryRouter initialEntries={['/projects/acme/tickets']}>
      <Routes>
        <Route path="/projects/:projectId/tickets" element={<ProjectTicketsPage />} />
        <Route path="/projects/:projectId/tickets/:id" element={<div>Ticket Detail</div>} />
      </Routes>
    </MemoryRouter>
  )
}

// ── AC1: four columns ────────────────────────────────────────────────────────

describe('T187 — AC1: Tickets displayed in four columns', () => {
  it('renders Queued, Running, Waiting Human and Done column headers', async () => {
    renderBoard()
    expect(await screen.findByText('Queued')).toBeInTheDocument()
    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByText('Waiting Human')).toBeInTheDocument()
    expect(screen.getByText('Done')).toBeInTheDocument()
  })

  it('places tickets in correct columns', async () => {
    renderBoard([QUEUED_TICKET, RUNNING_TICKET, WAITING_TICKET, DONE_TICKET])
    expect(await screen.findByText('T001')).toBeInTheDocument()
    expect(screen.getByText('T002')).toBeInTheDocument()
    expect(screen.getByText('T003')).toBeInTheDocument()
    expect(screen.getByText('T004')).toBeInTheDocument()
  })

  it('shows column ticket counts', async () => {
    renderBoard([QUEUED_TICKET, RUNNING_TICKET])
    await screen.findByText('T001')
    const counts = screen.getAllByText('1')
    expect(counts.length).toBeGreaterThanOrEqual(2)
  })
})

// ── AC2: Waiting Human tickets immediately visible ───────────────────────────

describe('T187 — AC2: Human-gate tickets immediately visible', () => {
  it('applies ring highlight to waiting-human cards', async () => {
    renderBoard([WAITING_TICKET])
    const card = await screen.findByText('T003')
    expect(card.closest('button')).toHaveClass('ring-2')
    expect(card.closest('button')).toHaveClass('ring-orange-400')
  })

  it('does not apply ring to non-waiting cards', async () => {
    renderBoard([QUEUED_TICKET])
    const card = await screen.findByText('T001')
    expect(card.closest('button')).not.toHaveClass('ring-2')
  })
})

// ── AC3: Clicking opens preview panel ───────────────────────────────────────

describe('T187 — AC3: Clicking a ticket opens preview panel', () => {
  it('opens preview panel on card click', async () => {
    renderBoard([QUEUED_TICKET])
    const card = await screen.findByText('T001')
    await act(async () => { fireEvent.click(card.closest('button')) })
    await screen.findByText('Open ticket')
  })

  it('preview panel is hidden before clicking', async () => {
    renderBoard([QUEUED_TICKET])
    await screen.findByText('T001')
    expect(screen.queryByText('Open ticket')).not.toBeInTheDocument()
  })
})

// ── AC4: Preview contains metadata and navigation links ──────────────────────

describe('T187 — AC4: Preview shows ticket metadata and navigation links', () => {
  beforeEach(() => {
    ticketsApi.getTicketTimeline.mockResolvedValue({ data: { last_error: 'test error' } })
  })

  async function openPreview(ticket) {
    renderBoard([ticket])
    const card = await screen.findByText(ticket.ticket_id)
    await act(async () => { fireEvent.click(card.closest('button')) })
  }

  it('shows ticket id in preview header', async () => {
    await openPreview(QUEUED_TICKET)
    const ids = await screen.findAllByText('T001')
    expect(ids.length).toBeGreaterThanOrEqual(2)
  })

  it('shows current state badge in preview', async () => {
    await openPreview(QUEUED_TICKET)
    const badges = await screen.findAllByText('QUEUED')
    expect(badges.length).toBeGreaterThanOrEqual(1)
  })

  it('shows branch name in preview panel', async () => {
    await openPreview(QUEUED_TICKET)
    const branches = await screen.findAllByText('ticket/T001')
    expect(branches.length).toBeGreaterThanOrEqual(1)
  })

  it('shows last error from timeline in preview', async () => {
    await openPreview(QUEUED_TICKET)
    await screen.findByText('test error')
  })

  it('shows GitHub issue link when repo and issue_number present', async () => {
    await openPreview(QUEUED_TICKET)
    const link = await screen.findByText('#10')
    expect(link).toHaveAttribute('href', 'https://github.com/org/repo/issues/10')
  })

  it('shows Open ticket action button', async () => {
    await openPreview(QUEUED_TICKET)
    await screen.findByText('Open ticket')
  })

  it('shows Open GitHub issue action button when issue present', async () => {
    await openPreview(QUEUED_TICKET)
    expect(await screen.findByText('Open GitHub issue')).toBeInTheDocument()
  })

  it('shows Open PR action button', async () => {
    await openPreview(QUEUED_TICKET)
    expect(await screen.findByText(/open pr/i)).toBeInTheDocument()
  })
})

// ── AC5: Existing ticket pages accessible from preview ───────────────────────

describe('T187 — AC5: Existing ticket pages still accessible', () => {
  it('Open ticket button links to detail route', async () => {
    renderBoard([QUEUED_TICKET])
    const card = await screen.findByText('T001')
    await act(async () => { fireEvent.click(card.closest('button')) })
    const openBtn = await screen.findByRole('link', { name: /open ticket/i })
    expect(openBtn).toHaveAttribute('href', '/projects/acme/tickets/T001')
  })
})

// ── Status mapping unit tests ────────────────────────────────────────────────

describe('T187 — status column mapping', () => {
  it('maps QUEUED, READY, PLANNED to queued', () => {
    expect(columnForState('QUEUED')).toBe('queued')
    expect(columnForState('READY')).toBe('queued')
    expect(columnForState('PLANNED')).toBe('queued')
  })

  it('maps IMPLEMENTING, TESTING, REVIEWING to running', () => {
    expect(columnForState('IMPLEMENTING')).toBe('running')
    expect(columnForState('TESTING')).toBe('running')
    expect(columnForState('REVIEWING')).toBe('running')
  })

  it('maps PLAN_REVIEW_NEEDED, IMPLEMENTATION_REVIEW_NEEDED, CONFLICT_RESOLUTION_NEEDED to waiting_human', () => {
    expect(columnForState('PLAN_REVIEW_NEEDED')).toBe('waiting_human')
    expect(columnForState('IMPLEMENTATION_REVIEW_NEEDED')).toBe('waiting_human')
    expect(columnForState('CONFLICT_RESOLUTION_NEEDED')).toBe('waiting_human')
  })

  it('maps TEST_COMPLETE, COMPLETED, MERGED, ARCHIVED to done', () => {
    expect(columnForState('TEST_COMPLETE')).toBe('done')
    expect(columnForState('COMPLETED')).toBe('done')
    expect(columnForState('MERGED')).toBe('done')
    expect(columnForState('ARCHIVED')).toBe('done')
  })

  it('defaults unknown state to queued', () => {
    expect(columnForState('UNKNOWN_STATE')).toBe('queued')
  })

  it('exports exactly four column definitions', () => {
    expect(COLUMN_DEFS).toHaveLength(4)
    const ids = COLUMN_DEFS.map(c => c.id)
    expect(ids).toContain('queued')
    expect(ids).toContain('running')
    expect(ids).toContain('waiting_human')
    expect(ids).toContain('done')
  })
})
