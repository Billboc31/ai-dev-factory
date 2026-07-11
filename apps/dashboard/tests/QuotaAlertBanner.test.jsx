import { render, screen } from '@testing-library/react'
import { ActiveProjectContext } from '../src/App'
import QuotaAlertBanner from '../src/components/QuotaAlertBanner'
import * as daemonApi from '../src/api/daemon'

vi.mock('../src/api/daemon')

function renderWithProject(projectId = 'demo') {
  return render(
    <ActiveProjectContext.Provider value={projectId}>
      <QuotaAlertBanner />
    </ActiveProjectContext.Provider>
  )
}

describe('QuotaAlertBanner', () => {
  it('renders nothing when quota alert is inactive', async () => {
    daemonApi.getRuntimeStatus.mockResolvedValue({
      data: { provider_quota_alert: { active: false } },
    })
    renderWithProject()
    await vi.waitFor(() => {
      expect(daemonApi.getRuntimeStatus).toHaveBeenCalled()
    })
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows quota banner when alert is active', async () => {
    daemonApi.getRuntimeStatus.mockResolvedValue({
      data: {
        provider_quota_alert: {
          active: true,
          provider: 'claude',
          message: "You've hit your limit",
          reset_at: '2026-06-26T19:40:00Z',
          cooldown_until: '2026-06-26T19:40:00Z',
          affected_tickets: ['T001'],
        },
      },
    })
    renderWithProject()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByText(/quota claude atteint/i)).toBeInTheDocument()
    expect(screen.getByText(/T001/)).toBeInTheDocument()
  })
})
