import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProjectTicketsPage from '../src/pages/ProjectTicketsPage'
import TicketPreviewPanel from '../src/components/TicketPreviewPanel'
import { columnForState, COLUMN_DEFS, stateBadgeClass } from '../src/lib/ticketColumns'
import * as projectsApi from '../src/api/projects'
import * as ticketsApi from '../src/api/tickets'
import usePolling from '../src/hooks/usePolling'

vi.mock('../src/api/projects')
vi.mock('../src/api/tickets')
vi.mock('../src/hooks/usePolling')

const QUEUED_TICKET = { ticket_id: 'T001', state: 'QUEUED', branch: 'ticket/T001', issue_number: 10, updated_at: '2026-06-01T10:00:00Z', last_log: 'queued' }
const RUNNING_TICKET = { ticket_id: 'T002', state: 'IMPLEMENTING', branch: 'ticket/T002', issue_number: 20, updated_at: '2026-06-01T11:00:00Z', last_log: 'running' }
const WAITING_TICKET = { ticket_id: 'T003', state: 'PLAN_REVIEW_NEEDED', branch: 'ticket/T003', issue_number: 30, updated_at: '2026-06-01T12:00:00Z', last_log: 'waiting' }
const DONE_TICKET = { ticket_id: 'T004', state: 'COMPLETED', branch: 'ticket/T004', issue_number: 40, updated_at: '2026-06-01T13:00:00Z', last_log: 'done' }

function renderBoard(tickets = []) {
  usePolling.mockImplementation((callback) => { callback() })
  projectsApi.getProject.mockResolvedValue({ data: { github_repo: 'org/repo' } })
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
  beforeEach(() => {
    ticketsApi.getTicketTimeline.mockResolvedValue({ data: { last_error: null } })
  })

  it('opens preview panel on card click', async () => {
    renderBoard([QUEUED_TICKET])
    const card = await screen.findByText('T001')
    fireEvent.click(card.closest('button'))
    await screen.findByText('Open ticket')
  })

  it('preview panel is not visible before clicking', async () => {
    renderBoard([QUEUED_TICKET])
    await screen.findByText('T001')
    expect(screen.queryByText('Open ticket')).not.toBeInTheDocument()
  })
})

// ── AC4: Preview contains metadata and navigation links ──────────────────────

describe('T187 — AC4: Preview shows ticket metadata and navigation links', () => {
  beforeEach(() => {
    ticketsApi.getTicketTimeline.mockResolvedValue({ data: { last_error: 'some error' } })
  })

  it('shows ticket id in preview header', async () => {
    renderBoard([QUEUED_TICKET])
    fireEvent.click((await screen.findByText('T001')).closest('button'))
    const headings = await screen.findAllByText('T001')
    expect(headings.length).toBeGreaterThanOrEqual(2)
  })

  it('shows current state badge in preview', async () => {
    renderBoard([QUEUED_TICKET])
    fireEvent.click((await screen.findByText('T001')).closest('button'))
    const stateBadges = await screen.findAllByText('QUEUED')
    expect(stateBadges.length).toBeGreaterThanOrEqual(1)
  })

  it('shows branch name in preview', async () => {
    renderBoard([QUEUED_TICKET])
    fireEvent.click((await screen.findByText('T001')).closest('button'))
    await screen.findByText('ticket/T001')
  })

  it('shows last error from timeline in preview', async () => {
    renderBoard([QUEUED_TICKET])
    fireEvent.click((await screen.findByText('T001')).closest('button'))
    await screen.findByText('some error')
  })

  it('shows GitHub issue link when repo and issue_number present', async () => {
    renderBoard([QUEUED_TICKET])
    fireEvent.click((await screen.findByText('T001')).closest('button'))
    const issueLink = await screen.findByText('#10')
    expect(issueLink).toHaveAttribute('href', 'https://github.com/org/repo/issues/10')
  })

  it('shows Open ticket action button', async () => {
    renderBoard([QUEUED_TICKET])
    fireEvent.click((await screen.findByText('T001')).closest('button'))
    await screen.findByText('Open ticket')
  })

  it('shows Open GitHub issue action button when issue present', async () => {
    renderBoard([QUEUED_TICKET])
    fireEvent.click((await screen.findByText('T001')).closest('button'))
    const btn = await screen.findByText('Open GitHub issue')
    expect(btn).toBeInTheDocument()
  })

  it('shows Open PR action button', async () => {
    renderBoard([QUEUED_TICKET])
    fireEvent.click((await screen.findByText('T001')).closest('button'))
    await screen.findByText(/open pr/i)
  })
})

// ── AC5: Existing ticket pages still work ───────────────────────────────────

describe('T187 — AC5: Existing ticket pages still accessible', () => {
  it('navigating Open ticket from preview goes to detail route', async () => {
    ticketsApi.getTicketTimeline.mockResolvedValue({ data: { last_error: null } })
    renderBoard([QUEUED_TICKET])
    fireEvent.click((await screen.findByText('T001')).closest('button'))
    const openBtn = await screen.findByRole('link', { name: /open ticket/i })
    expect(openBtn).toHaveAttribute('href', '/projects/acme/tickets/T001')
  })
})

// ── Status mapping ───────────────────────────────────────────────────────────

describe('T187 — status column mapping', () => {
  it('maps QUEUED, READY, PLANNED to queued column', () => {
    expect(columnForState('QUEUED')).toBe('queued')
    expect(columnForState('READY')).toBe('queued')
    expect(columnForState('PLANNED')).toBe('queued')
  })

  it('maps IMPLEMENTING, TESTING, REVIEWING to running column', () => {
    expect(columnForState('IMPLEMENTING')).toBe('running')
    expect(columnForState('TESTING')).toBe('running')
    expect(columnForState('REVIEWING')).toBe('running')
  })

  it('maps PLAN_REVIEW_NEEDED, IMPLEMENTATION_REVIEW_NEEDED, CONFLICT_RESOLUTION_NEEDED to waiting_human', () => {
    expect(columnForState('PLAN_REVIEW_NEEDED')).toBe('waiting_human')
    expect(columnForState('IMPLEMENTATION_REVIEW_NEEDED')).toBe('waiting_human')
    expect(columnForState('CONFLICT_RESOLUTION_NEEDED')).toBe('waiting_human')
  })

  it('maps TEST_COMPLETE, COMPLETED, MERGED, ARCHIVED to done column', () => {
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
