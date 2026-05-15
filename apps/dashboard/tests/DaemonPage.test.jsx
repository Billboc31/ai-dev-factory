import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import DaemonPage from '../src/pages/DaemonPage'
import * as daemonApi from '../src/api/daemon'

vi.mock('../src/api/daemon')

function renderPage() {
  return render(
    <MemoryRouter>
      <DaemonPage />
    </MemoryRouter>
  )
}

describe('DaemonPage', () => {
  it('renders the page heading', async () => {
    daemonApi.getDaemonStatus.mockResolvedValue({ data: { running: false, pid: null, started_at: null } })
    renderPage()
    expect(await screen.findByRole('heading', { name: /daemon/i })).toBeInTheDocument()
  })

  it('shows running status when daemon is active', async () => {
    daemonApi.getDaemonStatus.mockResolvedValue({
      data: { running: true, pid: 1234, started_at: '2026-05-15T08:00:00Z' }
    })
    renderPage()
    expect(await screen.findByText('Running')).toBeInTheDocument()
    expect(await screen.findByText('1234')).toBeInTheDocument()
  })

  it('shows stopped status when daemon is inactive', async () => {
    daemonApi.getDaemonStatus.mockResolvedValue({
      data: { running: false, pid: null, started_at: null }
    })
    renderPage()
    expect(await screen.findByText('Stopped')).toBeInTheDocument()
  })

  it('renders start, stop, and restart buttons', async () => {
    daemonApi.getDaemonStatus.mockResolvedValue({ data: { running: false, pid: null, started_at: null } })
    renderPage()
    expect(await screen.findByRole('button', { name: 'Start' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Stop' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Restart' })).toBeInTheDocument()
  })

  it('calls startDaemon and refreshes status when start is clicked', async () => {
    daemonApi.getDaemonStatus.mockResolvedValue({ data: { running: false, pid: null, started_at: null } })
    daemonApi.startDaemon.mockResolvedValue({ data: { ok: true, message: 'Daemon started' } })

    renderPage()
    const btn = await screen.findByRole('button', { name: 'Start' })
    await userEvent.click(btn)

    expect(daemonApi.startDaemon).toHaveBeenCalled()
    expect(await screen.findByText('Daemon started')).toBeInTheDocument()
  })

  it('shows error banner on API failure', async () => {
    daemonApi.getDaemonStatus.mockRejectedValue({ message: 'Connection refused' })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Connection refused')
  })
})
