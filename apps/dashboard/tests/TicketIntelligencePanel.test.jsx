import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import TicketIntelligencePanel from '../src/components/TicketIntelligencePanel'
import * as ticketsApi from '../src/api/tickets'
import usePolling from '../src/hooks/usePolling'

vi.mock('../src/api/tickets')
vi.mock('../src/hooks/usePolling')

const TICKET_ID = 'T197'
const PROJECT_ID = 'test-project'

const COMPLETED_INTELLIGENCE = {
  ticket_id: TICKET_ID,
  analysis_status: 'completed',
  difficulty_score: 6,
  difficulty_label: 'medium',
  risk_score: 5,
  risk_label: 'moderate',
  complexity_factors: ['backend', 'database', 'UI'],
  recommended_model: 'advanced-reasoning-model',
  recommended_model_reason: 'Requires architecture reasoning.',
  estimated_cost_min: 0.05,
  estimated_cost_max: 0.35,
  cost_currency: 'USD',
  cost_estimate_status: 'estimated',
  queue_rank: 20,
  queue_reason: 'Backend foundation first.',
  dependency_hints: ['T001'],
  parallel_safe_candidate: false,
  requires_human_plan_review: true,
  human_plan_review_reason: 'DB schema change.',
  requires_human_code_review: false,
  human_code_review_reason: null,
  autonomous_execution_recommendation: 'plan_review_required',
  analysis_summary: 'This ticket is medium difficulty and moderate risk.',
  updated_at: '2026-06-20T10:00:00Z',
}

function renderPanel() {
  return render(<TicketIntelligencePanel ticketId={TICKET_ID} projectId={PROJECT_ID} />)
}

describe('TicketIntelligencePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    usePolling.mockImplementation(() => {})
  })

  it('shows advisory badge always', async () => {
    ticketsApi.getTicketIntelligence.mockRejectedValue({ response: { status: 404 } })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Advisory only/)).toBeInTheDocument()
    })
  })

  it('shows "No analysis yet" when no analysis exists', async () => {
    ticketsApi.getTicketIntelligence.mockRejectedValue({ response: { status: 404 } })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/No analysis yet/)).toBeInTheDocument()
    })
  })

  it('shows Analyze button when no analysis', async () => {
    ticketsApi.getTicketIntelligence.mockRejectedValue({ response: { status: 404 } })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Analyze' })).toBeInTheDocument()
    })
  })

  it('shows completed analysis fields', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getAllByText(/medium/).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/moderate/).length).toBeGreaterThan(0)
      expect(screen.getByText('advanced-reasoning-model')).toBeInTheDocument()
      expect(screen.getByText(/Requires architecture reasoning/)).toBeInTheDocument()
    })
  })

  it('shows analysis summary when completed', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/medium difficulty and moderate risk/)).toBeInTheDocument()
    })
  })

  it('shows Re-analyze button when completed', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Re-analyze' })).toBeInTheDocument()
    })
  })

  it('shows human plan review recommendation', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText('Required')).toBeInTheDocument()
      expect(screen.getByText(/DB schema change/)).toBeInTheDocument()
    })
  })

  it('shows dependency hints', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText('T001')).toBeInTheDocument()
    })
  })

  it('shows queue rank', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/#20/)).toBeInTheDocument()
    })
  })

  it('shows running state with animation text', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({
      data: { ticket_id: TICKET_ID, analysis_status: 'running' }
    })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Analysis in progress/)).toBeInTheDocument()
    })
  })

  it('shows "Analysis running" on button when active', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({
      data: { ticket_id: TICKET_ID, analysis_status: 'running' }
    })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analysis running/ })).toBeInTheDocument()
    })
  })

  it('shows failed state with error message', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({
      data: {
        ticket_id: TICKET_ID,
        analysis_status: 'failed',
        analysis_summary: 'Analysis timed out after 120 seconds.',
      }
    })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Analysis failed/)).toBeInTheDocument()
      expect(screen.getByText(/timed out after 120 seconds/)).toBeInTheDocument()
    })
  })

  it('shows Retry analysis button when failed', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({
      data: { ticket_id: TICKET_ID, analysis_status: 'failed', analysis_summary: 'error' }
    })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Retry analysis' })).toBeInTheDocument()
    })
  })

  it('calls analyzeTicketIntelligence when Analyze is clicked', async () => {
    const user = userEvent.setup()
    ticketsApi.getTicketIntelligence.mockRejectedValue({ response: { status: 404 } })
    ticketsApi.analyzeTicketIntelligence.mockResolvedValue({
      data: { ticket_id: TICKET_ID, analysis_status: 'queued' }
    })
    renderPanel()
    await waitFor(() => screen.getByRole('button', { name: 'Analyze' }))
    await user.click(screen.getByRole('button', { name: 'Analyze' }))
    expect(ticketsApi.analyzeTicketIntelligence).toHaveBeenCalledWith(TICKET_ID, PROJECT_ID)
  })

  it('polls while status is queued', async () => {
    let capturedDelay = null
    usePolling.mockImplementation((_cb, delay) => { capturedDelay = delay })
    ticketsApi.getTicketIntelligence.mockResolvedValue({
      data: { ticket_id: TICKET_ID, analysis_status: 'queued' }
    })
    renderPanel()
    await waitFor(() => {
      expect(capturedDelay).not.toBeNull()
      expect(capturedDelay).toBeGreaterThan(0)
    })
  })

  it('stops polling when completed', async () => {
    let capturedDelay = null
    usePolling.mockImplementation((_cb, delay) => { capturedDelay = delay })
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(capturedDelay).toBeNull()
    })
  })

  it('shows cost estimate when available', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/\$0.050.*\$0.350/)).toBeInTheDocument()
    })
  })
})
