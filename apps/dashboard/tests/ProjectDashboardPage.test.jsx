import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProjectDashboardPage from '../src/pages/ProjectDashboardPage'
import * as daemonApi from '../src/api/daemon'
import * as projectsApi from '../src/api/projects'
import * as ticketsApi from '../src/api/tickets'
import usePolling from '../src/hooks/usePolling'

vi.mock('../src/api/daemon')
vi.mock('../src/api/projects')
vi.mock('../src/api/tickets')
vi.mock('../src/hooks/usePolling')
vi.mock('../src/components/RuntimeStatusPanel', () => ({ default: () => <div>RuntimeStatusPanel</div> }))
vi.mock('../src/components/DaemonActivityFeed', () => ({ default: () => <div>DaemonActivityFeed</div> }))

const PROJECT_ID = 'my-project'

function renderPage(projectId = PROJECT_ID) {
  return render(
    <MemoryRouter initialEntries={[`/projects/${projectId}/dashboard`]}>
      <Routes>
        <Route path="/projects/:projectId/dashboard" element={<ProjectDashboardPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProjectDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    usePolling.mockImplementation((callback) => { callback() })
    projectsApi.listProjects.mockResolvedValue({
      data: [{ name: PROJECT_ID, stack: 'python', root: '/home/user/my-project', runtime_root: '/tmp/runtime/my-project' }],
    })
    daemonApi.getDaemonStatus.mockResolvedValue({
      data: { running: false, pid: null, started_at: null },
    })
    daemonApi.getBoardData.mockResolvedValue({ data: { columns: [] } })
    ticketsApi.listTickets.mockResolvedValue({ data: [] })
  })

  it('renders the project name as heading', async () => {
    renderPage()
    expect(await screen.findByRole('heading', { name: PROJECT_ID })).toBeInTheDocument()
  })

  it('displays daemon running status', async () => {
    daemonApi.getDaemonStatus.mockResolvedValue({
      data: { running: true, pid: 4242, started_at: new Date().toISOString() },
    })
    renderPage()
    expect(await screen.findByText('Running')).toBeInTheDocument()
    expect(await screen.findByText('4242')).toBeInTheDocument()
  })

  it('displays daemon stopped status', async () => {
    renderPage()
    expect(await screen.findByText('Stopped')).toBeInTheDocument()
  })

  it('renders Start daemon, Stop daemon, and Restart buttons', async () => {
    renderPage()
    expect(await screen.findByRole('button', { name: 'Start daemon' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Stop daemon' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restart' })).toBeInTheDocument()
  })

  it('calls startDaemon with projectId when Start daemon is clicked', async () => {
    daemonApi.startDaemon.mockResolvedValue({ data: { ok: true, message: 'Started' } })
    renderPage()
    const btn = await screen.findByRole('button', { name: 'Start daemon' })
    await userEvent.click(btn)
    expect(daemonApi.startDaemon).toHaveBeenCalledWith(PROJECT_ID)
  })

  it('calls stopDaemon with projectId when Stop daemon is clicked', async () => {
    daemonApi.stopDaemon.mockResolvedValue({ data: { ok: true, message: 'Stopped' } })
    renderPage()
    const btn = await screen.findByRole('button', { name: 'Stop daemon' })
    await userEvent.click(btn)
    expect(daemonApi.stopDaemon).toHaveBeenCalledWith(PROJECT_ID)
  })

  it('shows host command banner when startDaemon returns host_command', async () => {
    const hostCmd = 'cd /host && python run_daemon.py'
    daemonApi.startDaemon.mockResolvedValue({
      data: { ok: false, message: 'Cannot start inside Docker.', host_command: hostCmd },
    })
    renderPage()
    const btn = await screen.findByRole('button', { name: 'Start daemon' })
    await userEvent.click(btn)
    expect(await screen.findByText(/Run on host/i)).toBeInTheDocument()
    expect(screen.getByText(hostCmd)).toBeInTheDocument()
  })

  it('shows error banner on getDaemonStatus failure', async () => {
    daemonApi.getDaemonStatus.mockRejectedValue({ message: 'Connection refused' })
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Connection refused')
  })

  it('displays project stack badge and root path', async () => {
    renderPage()
    expect(await screen.findByText('python')).toBeInTheDocument()
    expect(await screen.findByText('/home/user/my-project')).toBeInTheDocument()
  })

  it('calls listTickets to populate active ticket count', async () => {
    ticketsApi.listTickets.mockResolvedValue({
      data: [
        { ticket_id: 'T001', state: 'RUNNING' },
        { ticket_id: 'T002', state: 'COMPLETE' },
      ],
    })
    renderPage()
    await waitFor(() => expect(ticketsApi.listTickets).toHaveBeenCalledWith(PROJECT_ID))
    expect(await screen.findByText('1')).toBeInTheDocument()
  })
})
