import { render, screen } from '@testing-library/react'
import DaemonActivityFeed from '../src/components/DaemonActivityFeed'
import * as daemonApi from '../src/api/daemon'

vi.mock('../src/api/daemon')

describe('DaemonActivityFeed', () => {
  it('shows activity lines when present', async () => {
    daemonApi.getDaemonActivity.mockResolvedValue({
      data: { lines: ['[10:00:00] daemon started', '[10:00:01] T030 planner started'] }
    })
    render(<DaemonActivityFeed />)
    expect(await screen.findByText('[10:00:00] daemon started')).toBeInTheDocument()
    expect(await screen.findByText('[10:00:01] T030 planner started')).toBeInTheDocument()
  })

  it('shows empty message when no activity', async () => {
    daemonApi.getDaemonActivity.mockResolvedValue({ data: { lines: [] } })
    render(<DaemonActivityFeed />)
    expect(await screen.findByText(/aucune activité/i)).toBeInTheDocument()
  })

  it('shows error message on API failure', async () => {
    daemonApi.getDaemonActivity.mockRejectedValue(new Error('Network Error'))
    render(<DaemonActivityFeed />)
    expect(await screen.findByText(/unable to load activity feed/i)).toBeInTheDocument()
  })

  it('passes custom lines count to API', async () => {
    daemonApi.getDaemonActivity.mockResolvedValue({ data: { lines: [] } })
    render(<DaemonActivityFeed lines={20} />)
    expect(daemonApi.getDaemonActivity).toHaveBeenCalledWith(20)
  })
})
