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

const COMPLETED_INTELLIGENCE_WITH_SIGNALS = {
  ...COMPLETED_INTELLIGENCE,
  computed_signals_json: { foo: 'bar', n: 3 },
}

function renderPanel() {
  return render(<TicketIntelligencePanel ticketId={TICKET_ID} projectId={PROJECT_ID} />)
}

async function expandDetailedAnalysis(user) {
  const summary = await screen.findByText('Show detailed analysis')
  await user.click(summary)
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

  it('shows completed analysis compact fields', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getAllByText(/medium/).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/moderate/).length).toBeGreaterThan(0)
      expect(screen.getByText('advanced-reasoning-model')).toBeInTheDocument()
    })
  })

  it('shows analysis summary when completed', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getAllByText(/medium difficulty and moderate risk/).length).toBeGreaterThan(0)
    })
  })

  it('shows Re-analyze button when completed', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Re-analyze' })).toBeInTheDocument()
    })
  })

  it('shows human plan review recommendation (reason behind detailed disclosure)', async () => {
    const user = userEvent.setup()
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText('Required')).toBeInTheDocument()
    })
    const reason = screen.getByText(/DB schema change/)
    expect(reason.closest('details').open).toBe(false)
    await expandDetailedAnalysis(user)
    expect(reason.closest('details').open).toBe(true)
  })

  it('shows dependency hints in compact view', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getAllByText('T001').length).toBeGreaterThan(0)
    })
  })

  it('shows queue rank behind detailed analysis disclosure', async () => {
    const user = userEvent.setup()
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => screen.getByText('Show detailed analysis'))
    const rank = screen.getByText(/#20/)
    expect(rank.closest('details').open).toBe(false)
    await expandDetailedAnalysis(user)
    expect(rank.closest('details').open).toBe(true)
  })

  it('shows running state with current stage label', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({
      data: {
        ticket_id: TICKET_ID,
        analysis_status: 'running',
        stage: 'waiting_ai',
        started_at: '2026-06-23T15:00:00Z',
      }
    })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Current stage: Waiting for AI response/)).toBeInTheDocument()
      expect(screen.getByText(/Started:/)).toBeInTheDocument()
      expect(screen.getByText(/Running for:/)).toBeInTheDocument()
    })
  })

  it('falls back to "Running" when stage missing on a running analysis', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({
      data: { ticket_id: TICKET_ID, analysis_status: 'running' }
    })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Current stage: Running/)).toBeInTheDocument()
    })
  })

  it('shows failed-during stage line when analysis failed mid-pipeline', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({
      data: {
        ticket_id: TICKET_ID,
        analysis_status: 'failed',
        analysis_summary: 'AI call failed (rc=2): boom',
        stage: 'waiting_ai',
        failure_origin: 'nonzero_rc',
      }
    })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText(/Failed during:/)).toBeInTheDocument()
      expect(screen.getByText(/Waiting for AI response/)).toBeInTheDocument()
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

  it('compact view shows key fields without expanding', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText('Difficulty')).toBeInTheDocument()
    })
    expect(screen.getByText('Risk')).toBeInTheDocument()
    expect(screen.getByText('Estimated cost')).toBeInTheDocument()
    expect(screen.getByText('Recommended model')).toBeInTheDocument()
    expect(screen.getByText('Plan review')).toBeInTheDocument()
    expect(screen.getByText('Code review')).toBeInTheDocument()
    expect(screen.getByText('Dependencies')).toBeInTheDocument()
    expect(screen.getByText('Parallel safe')).toBeInTheDocument()
    expect(screen.getByText('Autonomous execution')).toBeInTheDocument()
    expect(screen.getByText('Last analyzed')).toBeInTheDocument()
    expect(screen.getByText('Difficulty').closest('details')).toBeNull()
  })

  it('detailed analysis is collapsed by default', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    const summary = await screen.findByText('Show detailed analysis')
    expect(summary).toBeInTheDocument()
    const details = summary.closest('details')
    expect(details.open).toBe(false)
    expect(screen.getByText('Requires architecture reasoning.').closest('details')).toBe(details)
    expect(screen.getByText('DB schema change.').closest('details')).toBe(details)
    expect(screen.getByText(/#20/).closest('details')).toBe(details)
  })

  it('clicking Show detailed analysis reveals verbose fields', async () => {
    const user = userEvent.setup()
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await expandDetailedAnalysis(user)
    expect(screen.getByText('Requires architecture reasoning.')).toBeInTheDocument()
    expect(screen.getByText('DB schema change.')).toBeInTheDocument()
    expect(screen.getByText(/#20/)).toBeInTheDocument()
  })

  it('raw intelligence section is absent when computed_signals_json missing', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE })
    renderPanel()
    await waitFor(() => screen.getByText('Show detailed analysis'))
    expect(screen.queryByText('Show raw intelligence data')).not.toBeInTheDocument()
  })

  it('raw intelligence section is collapsed by default when present', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE_WITH_SIGNALS })
    renderPanel()
    const summary = await screen.findByText('Show raw intelligence data')
    const details = summary.closest('details')
    expect(details.open).toBe(false)
    expect(screen.getByText(/"foo": "bar"/).closest('details')).toBe(details)
  })

  it('clicking Show raw intelligence data reveals JSON', async () => {
    const user = userEvent.setup()
    ticketsApi.getTicketIntelligence.mockResolvedValue({ data: COMPLETED_INTELLIGENCE_WITH_SIGNALS })
    renderPanel()
    const summary = await screen.findByText('Show raw intelligence data')
    await user.click(summary)
    expect(screen.getByText(/"foo": "bar"/)).toBeInTheDocument()
  })

  it('missing optional fields do not crash', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({
      data: { ticket_id: TICKET_ID, analysis_status: 'completed' }
    })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText('Difficulty')).toBeInTheDocument()
    })
    expect(screen.getByText('Risk')).toBeInTheDocument()
    expect(screen.getByText('Recommended model')).toBeInTheDocument()
  })

  it('high risk applies warning border', async () => {
    ticketsApi.getTicketIntelligence.mockResolvedValue({
      data: {
        ticket_id: TICKET_ID,
        analysis_status: 'completed',
        risk_score: 9,
      }
    })
    const { container } = renderPanel()
    await waitFor(() => {
      expect(screen.getByText('Difficulty')).toBeInTheDocument()
    })
    expect(container.firstChild.className).toMatch(/border-orange-300/)
  })
})
