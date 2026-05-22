import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import RuntimeDashboardPage from '../src/pages/RuntimeDashboardPage'
import * as api from '../src/api/runtimeDashboard'

vi.mock('../src/api/runtimeDashboard')

const EMPTY_HEALTH = {
  supervisor_status: 'unknown',
  active_jobs: 0,
  stale_pid_files: [],
  stale_locks: [],
}

const SANDBOX_RUNNING = {
  id: 'sb-001',
  status: 'running',
  project_id: 'test-project',
  started_at: '2026-01-01T00:00:00Z',
  finished_at: null,
  ports: {},
  worktree_path: null,
  compose_project: null,
}

const SANDBOX_COMPLETED = {
  ...SANDBOX_RUNNING,
  status: 'completed',
  finished_at: '2026-01-01T01:00:00Z',
}

const PROPOSAL = {
  proposal_id: 'prop-001',
  sandbox_id: 'sb-001',
  status: 'completed',
  changed_files_count: 3,
  started_at: '2026-01-01T00:00:00Z',
  finished_at: '2026-01-01T01:00:00Z',
}

function renderPage() {
  return render(
    <MemoryRouter>
      <RuntimeDashboardPage />
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  api.listSandboxRuns.mockResolvedValue({ data: [] })
  api.listProposalRuns.mockResolvedValue({ data: [] })
  api.getRuntimeHealth.mockResolvedValue({ data: EMPTY_HEALTH })
})

describe('RuntimeDashboardPage', () => {
  it('renders all four sections', async () => {
    renderPage()
    expect(await screen.findByText('Sandbox Runs')).toBeInTheDocument()
    expect(screen.getByText('Proposal Runs')).toBeInTheDocument()
    expect(screen.getByText('Runtime Health')).toBeInTheDocument()
    expect(screen.getByText('Log Viewer')).toBeInTheDocument()
  })

  it('shows "no sandbox runs" message when list is empty', async () => {
    renderPage()
    expect(await screen.findByText(/no sandbox runs found/i)).toBeInTheDocument()
  })

  it('delete button is disabled when sandbox status is running', async () => {
    api.listSandboxRuns.mockResolvedValue({ data: [SANDBOX_RUNNING] })
    renderPage()
    const deleteBtn = await screen.findByRole('button', { name: /delete/i })
    expect(deleteBtn).toBeDisabled()
  })

  it('delete button is enabled when sandbox status is completed', async () => {
    api.listSandboxRuns.mockResolvedValue({ data: [SANDBOX_COMPLETED] })
    renderPage()
    const deleteBtn = await screen.findByRole('button', { name: /delete/i })
    expect(deleteBtn).not.toBeDisabled()
  })

  it('clicking delete on completed sandbox opens confirm dialog', async () => {
    api.listSandboxRuns.mockResolvedValue({ data: [SANDBOX_COMPLETED] })
    renderPage()
    const deleteBtn = await screen.findByRole('button', { name: /delete/i })
    await userEvent.click(deleteBtn)
    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('log drawer opens when Open Logs is clicked', async () => {
    api.listSandboxRuns.mockResolvedValue({ data: [SANDBOX_COMPLETED] })
    api.getSandboxLogs.mockResolvedValue({
      data: { content: 'log line 1\n', next_offset: 11 },
    })
    renderPage()
    const logsBtn = await screen.findByRole('button', { name: /open logs/i })
    await userEvent.click(logsBtn)
    expect(await screen.findByText(/log line 1/)).toBeInTheDocument()
  })

  it('log drawer shows sandbox id in header when open', async () => {
    api.listSandboxRuns.mockResolvedValue({ data: [SANDBOX_COMPLETED] })
    api.getSandboxLogs.mockResolvedValue({
      data: { content: '', next_offset: 0 },
    })
    renderPage()
    const logsBtn = await screen.findByRole('button', { name: /open logs/i })
    await userEvent.click(logsBtn)
    expect(await screen.findByText(/logs — sb-001/i)).toBeInTheDocument()
  })

  it('proposal summary modal renders on Open Summary click', async () => {
    api.listProposalRuns.mockResolvedValue({ data: [PROPOSAL] })
    api.getProposalSummary.mockResolvedValue({
      data: { proposal_id: 'prop-001', status: 'completed', changed_files_count: 3 },
    })
    renderPage()
    const summaryBtn = await screen.findByRole('button', { name: /open summary/i })
    await userEvent.click(summaryBtn)
    expect(await screen.findByText(/Proposal — prop-001/i)).toBeInTheDocument()
  })

  it('runtime health panel shows supervisor status', async () => {
    api.getRuntimeHealth.mockResolvedValue({
      data: { ...EMPTY_HEALTH, supervisor_status: 'up', active_jobs: 2 },
    })
    renderPage()
    expect(await screen.findByText('up')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })
})
