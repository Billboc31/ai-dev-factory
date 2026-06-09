import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProjectDashboardPage from '../src/pages/ProjectDashboardPage'
import ProjectTicketsPage from '../src/pages/ProjectTicketsPage'
import ProjectWorktreesPage from '../src/pages/ProjectWorktreesPage'
import ProjectLogsPage from '../src/pages/ProjectLogsPage'
import * as daemonApi from '../src/api/daemon'
import * as projectsApi from '../src/api/projects'
import * as ticketsApi from '../src/api/tickets'
import usePolling from '../src/hooks/usePolling'

vi.mock('../src/api/daemon')
vi.mock('../src/api/projects')
vi.mock('../src/api/tickets')
vi.mock('../src/hooks/usePolling')
vi.mock('../src/components/RuntimeStatusPanel', () => ({ default: () => null }))
vi.mock('../src/components/DaemonActivityFeed', () => ({ default: () => null }))

function renderRoute(path, element) {
  const pattern = path.replace(/\/[^/]+$/, '/:projectId') + (path.endsWith(':projectId') ? '' : '')
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/projects/:projectId/dashboard" element={<ProjectDashboardPage />} />
        <Route path="/projects/:projectId/tickets" element={<ProjectTicketsPage />} />
        <Route path="/projects/:projectId/worktrees" element={<ProjectWorktreesPage />} />
        <Route path="/projects/:projectId/logs" element={<ProjectLogsPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('Project-scoped routing smoke tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    usePolling.mockImplementation((callback) => { callback() })
    projectsApi.listProjects.mockResolvedValue({ data: [{ name: 'acme', stack: 'node', root: '/acme', runtime_root: '/rt/acme' }] })
    daemonApi.getDaemonStatus.mockResolvedValue({ data: { running: false, pid: null, started_at: null } })
    daemonApi.getBoardData.mockResolvedValue({ data: { columns: [] } })
    daemonApi.getDaemonActivity.mockResolvedValue({ data: { lines: [] } })
    daemonApi.getRuntimeStatus.mockResolvedValue({ data: { daemon_online: false, workers: [], runtime_root: '', daemon_log: '', supervisor_log: '', socket_path: '', pid_file: '' } })
    ticketsApi.listTickets.mockResolvedValue({ data: [] })
    projectsApi.listBranches.mockResolvedValue({ data: [] })
  })

  it('/projects/:projectId/dashboard renders the project dashboard', async () => {
    renderRoute('/projects/acme/dashboard')
    expect(await screen.findByRole('heading', { name: 'acme' })).toBeInTheDocument()
  })

  it('/projects/:projectId/tickets renders the tickets page heading', async () => {
    renderRoute('/projects/acme/tickets')
    expect(await screen.findByRole('heading', { name: /tickets/i })).toBeInTheDocument()
  })

  it('/projects/:projectId/worktrees renders the worktrees page heading', async () => {
    renderRoute('/projects/acme/worktrees')
    expect(await screen.findByRole('heading', { name: /worktrees/i })).toBeInTheDocument()
  })

  it('/projects/:projectId/logs renders the logs page heading', async () => {
    renderRoute('/projects/acme/logs')
    expect(await screen.findByRole('heading', { name: /logs/i })).toBeInTheDocument()
  })

  it('each page reads projectId from URL params (not hardcoded)', async () => {
    renderRoute('/projects/custom-project/dashboard')
    expect(await screen.findByRole('heading', { name: 'custom-project' })).toBeInTheDocument()
    expect(daemonApi.getDaemonStatus).toHaveBeenCalledWith('custom-project')
  })
})
