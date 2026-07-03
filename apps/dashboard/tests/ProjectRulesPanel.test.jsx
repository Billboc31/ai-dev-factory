import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProjectRulesPanel from '../src/components/ProjectRulesPanel'
import * as ticketsApi from '../src/api/tickets'

vi.mock('../src/api/tickets')

const PROJECT_ID = 'proj-a'

const MIXED_RULES = {
  project_id: PROJECT_ID,
  rules: [
    {
      rule_key: 'require_ticket_intelligence',
      enabled: true,
      configuration: {},
      description: 'Ticket Intelligence analysis must be completed.',
      default_enabled: true,
      default_configuration: {},
    },
    {
      rule_key: 'require_human_approval',
      enabled: true,
      configuration: {},
      description: 'Human approval required.',
      default_enabled: true,
      default_configuration: {},
    },
    {
      rule_key: 'max_estimated_cost_usd',
      enabled: false,
      configuration: { max_cost_usd: 0.5 },
      description: 'Block when cost exceeds limit.',
      default_enabled: false,
      default_configuration: { max_cost_usd: 0.5 },
    },
    {
      rule_key: 'max_difficulty',
      enabled: true,
      configuration: { max_difficulty: 7 },
      description: 'Block when difficulty exceeds limit.',
      default_enabled: false,
      default_configuration: { max_difficulty: 7 },
    },
    {
      rule_key: 'require_human_plan_approval',
      enabled: true,
      configuration: {},
      description:
        'Require Human Plan Approval. When disabled, implementation plans are automatically approved after generation. Useful for demos and fully automated projects.',
      default_enabled: true,
      default_configuration: {},
    },
  ],
}

function renderPanel() {
  return render(<ProjectRulesPanel projectId={PROJECT_ID} />)
}

describe('ProjectRulesPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders each rule with its key and description', async () => {
    ticketsApi.getProjectRules.mockResolvedValue({ data: MIXED_RULES })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByText('require_ticket_intelligence')).toBeInTheDocument()
      expect(screen.getByText('require_human_approval')).toBeInTheDocument()
      expect(screen.getByText('max_estimated_cost_usd')).toBeInTheDocument()
      expect(screen.getByText('max_difficulty')).toBeInTheDocument()
      expect(screen.getByText('require_human_plan_approval')).toBeInTheDocument()
      expect(screen.getByText(/Ticket Intelligence analysis must be completed/)).toBeInTheDocument()
      expect(
        screen.getByText(/Require Human Plan Approval/),
      ).toBeInTheDocument()
    })
  })

  it('renders an enable toggle per rule', async () => {
    ticketsApi.getProjectRules.mockResolvedValue({ data: MIXED_RULES })
    renderPanel()
    await waitFor(() => {
      expect(screen.getByLabelText('Toggle require_ticket_intelligence')).toBeChecked()
      expect(screen.getByLabelText('Toggle require_human_approval')).toBeChecked()
      expect(screen.getByLabelText('Toggle max_estimated_cost_usd')).not.toBeChecked()
      expect(screen.getByLabelText('Toggle max_difficulty')).toBeChecked()
    })
  })

  it('renders numeric input for threshold rules', async () => {
    ticketsApi.getProjectRules.mockResolvedValue({ data: MIXED_RULES })
    renderPanel()
    await waitFor(() => {
      const costInput = screen.getByLabelText(/Max estimated cost/)
      expect(costInput).toBeInTheDocument()
      expect(costInput).toHaveValue(0.5)
      const diffInput = screen.getByLabelText(/Max difficulty score/)
      expect(diffInput).toBeInTheDocument()
      expect(diffInput).toHaveValue(7)
    })
  })

  it('Save sends current state to PUT with rules payload', async () => {
    const user = userEvent.setup()
    ticketsApi.getProjectRules.mockResolvedValue({ data: MIXED_RULES })
    ticketsApi.putProjectRules.mockResolvedValue({ data: MIXED_RULES })

    renderPanel()
    await waitFor(() => screen.getByText('require_ticket_intelligence'))

    await user.click(screen.getByLabelText('Toggle max_estimated_cost_usd'))
    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(ticketsApi.putProjectRules).toHaveBeenCalledTimes(1)
    })
    const [pid, payload] = ticketsApi.putProjectRules.mock.calls[0]
    expect(pid).toBe(PROJECT_ID)
    expect(payload.rules).toBeDefined()
    const cost = payload.rules.find(r => r.rule_key === 'max_estimated_cost_usd')
    expect(cost.enabled).toBe(true)  // toggled from false to true
  })

  it('Reset to defaults calls PUT with action=reset_defaults', async () => {
    const user = userEvent.setup()
    ticketsApi.getProjectRules.mockResolvedValue({ data: MIXED_RULES })
    ticketsApi.putProjectRules.mockResolvedValue({ data: MIXED_RULES })

    renderPanel()
    await waitFor(() => screen.getByText('require_ticket_intelligence'))

    await user.click(screen.getByRole('button', { name: 'Reset to defaults' }))

    await waitFor(() => {
      expect(ticketsApi.putProjectRules).toHaveBeenCalledWith(
        PROJECT_ID,
        { action: 'reset_defaults' }
      )
    })
  })

  it('updates threshold input and includes new value on Save', async () => {
    const user = userEvent.setup()
    ticketsApi.getProjectRules.mockResolvedValue({ data: MIXED_RULES })
    ticketsApi.putProjectRules.mockResolvedValue({ data: MIXED_RULES })

    renderPanel()
    await waitFor(() => screen.getByText('max_difficulty'))

    const diffInput = screen.getByLabelText(/Max difficulty score/)
    await user.clear(diffInput)
    await user.type(diffInput, '4')

    await user.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => {
      expect(ticketsApi.putProjectRules).toHaveBeenCalledTimes(1)
    })
    const payload = ticketsApi.putProjectRules.mock.calls[0][1]
    const difficulty = payload.rules.find(r => r.rule_key === 'max_difficulty')
    expect(difficulty.configuration.max_difficulty).toBe(4)
  })
})
