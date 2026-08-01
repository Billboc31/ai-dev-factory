import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import ProjectWorkspacePanel from '../src/components/ProjectWorkspacePanel'
import * as workspaceApi from '../src/api/workspace'

vi.mock('../src/api/workspace')

beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn()
})

const REPO_PATH = '/host/secret/path/to/repo'

const _redeployAction = (overrides = {}) => ({
  capability: 'redeploy_project',
  description: 'Pull and redeploy backend and frontend',
  action_id: 'action-abc',
  project_id: 'my-project',
  safe_identifier: 'My Project',
  configured_branch: 'main',
  pull: true,
  components: ['backend', 'frontend'],
  has_dirty_warning: false,
  ...overrides,
})

function renderPanel(projectId = 'my-project') {
  return render(<ProjectWorkspacePanel projectId={projectId} isOpen onClose={() => {}} />)
}

function _mockChat(proposed_action = null, intent = 'informational') {
  workspaceApi.postWorkspaceMessage.mockResolvedValue({
    data: {
      reply: 'Sure, I will redeploy.',
      intent: proposed_action ? 'actionable' : intent,
      proposed_action,
      issue_draft: null,
      confirmation_required: !!proposed_action,
    },
  })
}

async function _submitMessage(text = 'redeploy this project') {
  const input = screen.getByRole('textbox')
  fireEvent.change(input, { target: { value: text } })
  fireEvent.submit(input.closest('form'))
}

describe('ProjectWorkspacePanel — redeploy confirmation card', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders safe_identifier, configured_branch, pull, and components', async () => {
    _mockChat(_redeployAction())
    renderPanel()
    await _submitMessage()

    await screen.findByText(/My Project/)
    expect(screen.getByText('main')).toBeInTheDocument()
    expect(screen.getByText('Yes')).toBeInTheDocument()
    expect(screen.getByText('backend, frontend')).toBeInTheDocument()
  })

  it('shows dirty warning badge when has_dirty_warning is true', async () => {
    _mockChat(_redeployAction({ has_dirty_warning: true }))
    renderPanel()
    await _submitMessage()

    await screen.findByText(/uncommitted changes/i)
  })

  it('does not display the host repository path', async () => {
    _mockChat(_redeployAction({ safe_identifier: 'My Project' }))
    renderPanel()
    await _submitMessage()

    await screen.findByText(/My Project/)
    expect(screen.queryByText(REPO_PATH)).toBeNull()
    expect(document.body.textContent).not.toContain(REPO_PATH)
  })

  it('confirm click sends only action_id to confirmWorkspaceAction', async () => {
    _mockChat(_redeployAction())
    workspaceApi.confirmWorkspaceAction.mockResolvedValue({
      data: { ok: true, result: 'Done.' },
    })
    renderPanel()
    await _submitMessage()

    const confirmBtn = await screen.findByText('Confirm')
    fireEvent.click(confirmBtn)

    await waitFor(() =>
      expect(workspaceApi.confirmWorkspaceAction).toHaveBeenCalledWith(
        'my-project',
        'action-abc',
      )
    )
    const callArgs = workspaceApi.confirmWorkspaceAction.mock.calls[0]
    expect(callArgs.length).toBe(2)
    expect(callArgs[1]).toBe('action-abc')
  })
})

describe('ProjectWorkspacePanel — deployment polling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows current stage spinner while deployment runs', async () => {
    _mockChat(_redeployAction())
    workspaceApi.confirmWorkspaceAction.mockResolvedValue({
      data: { ok: true, deployment_id: 'dep-1', status: 'RUNNING' },
    })
    workspaceApi.getDeploymentStatus.mockResolvedValue({
      data: { status: 'RUNNING', stage: 'BUILDING_backend' },
    })

    renderPanel()
    await act(async () => { await _submitMessage() })
    const confirmBtn = await screen.findByText('Confirm')
    await act(async () => { fireEvent.click(confirmBtn) })

    await waitFor(() =>
      expect(workspaceApi.confirmWorkspaceAction).toHaveBeenCalled()
    )
    await act(async () => { vi.advanceTimersByTime(2500) })

    await waitFor(() =>
      expect(workspaceApi.getDeploymentStatus).toHaveBeenCalledWith('my-project', 'dep-1')
    )
    await screen.findByText(/Building backend/i)
  })

  it('shows success bubble and stops polling on SUCCEEDED', async () => {
    _mockChat(_redeployAction())
    workspaceApi.confirmWorkspaceAction.mockResolvedValue({
      data: { ok: true, deployment_id: 'dep-2', status: 'RUNNING' },
    })
    workspaceApi.getDeploymentStatus.mockResolvedValue({
      data: {
        status: 'SUCCEEDED',
        stage: 'SUCCEEDED',
        deployed_sha: 'abc1234',
        preview_url: 'http://localhost:3000',
      },
    })

    renderPanel()
    await act(async () => { await _submitMessage() })
    const confirmBtn = await screen.findByText('Confirm')
    await act(async () => { fireEvent.click(confirmBtn) })

    await waitFor(() => expect(workspaceApi.confirmWorkspaceAction).toHaveBeenCalled())
    await act(async () => { vi.advanceTimersByTime(2500) })

    await screen.findByText(/Deployed successfully/i)
    await screen.findByText(/abc1234/)

    const callCountAfterSuccess = workspaceApi.getDeploymentStatus.mock.calls.length
    await act(async () => { vi.advanceTimersByTime(5000) })
    expect(workspaceApi.getDeploymentStatus.mock.calls.length).toBe(callCountAfterSuccess)
  })

  it('shows error and stops polling on FAILED', async () => {
    _mockChat(_redeployAction())
    workspaceApi.confirmWorkspaceAction.mockResolvedValue({
      data: { ok: true, deployment_id: 'dep-3', status: 'RUNNING' },
    })
    workspaceApi.getDeploymentStatus.mockResolvedValue({
      data: {
        status: 'FAILED',
        error_stage: 'PULLING',
        error_excerpt: 'fatal: could not read remote',
      },
    })

    renderPanel()
    await act(async () => { await _submitMessage() })
    const confirmBtn = await screen.findByText('Confirm')
    await act(async () => { fireEvent.click(confirmBtn) })

    await waitFor(() => expect(workspaceApi.confirmWorkspaceAction).toHaveBeenCalled())
    await act(async () => { vi.advanceTimersByTime(2500) })

    await screen.findByText(/PULLING/)
    await screen.findByText(/could not read remote/)

    const callCountAfterFailure = workspaceApi.getDeploymentStatus.mock.calls.length
    await act(async () => { vi.advanceTimersByTime(5000) })
    expect(workspaceApi.getDeploymentStatus.mock.calls.length).toBe(callCountAfterFailure)
  })

  it('shows error and stops polling on HTTP error from polling', async () => {
    _mockChat(_redeployAction())
    workspaceApi.confirmWorkspaceAction.mockResolvedValue({
      data: { ok: true, deployment_id: 'dep-4', status: 'RUNNING' },
    })
    workspaceApi.getDeploymentStatus.mockRejectedValue({
      response: { data: { detail: 'Supervisor unreachable' } },
      message: 'Network Error',
    })

    renderPanel()
    await act(async () => { await _submitMessage() })
    const confirmBtn = await screen.findByText('Confirm')
    await act(async () => { fireEvent.click(confirmBtn) })

    await waitFor(() => expect(workspaceApi.confirmWorkspaceAction).toHaveBeenCalled())
    await act(async () => { vi.advanceTimersByTime(2500) })

    await screen.findByText(/Supervisor unreachable/)

    const callCountAfterError = workspaceApi.getDeploymentStatus.mock.calls.length
    await act(async () => { vi.advanceTimersByTime(5000) })
    expect(workspaceApi.getDeploymentStatus.mock.calls.length).toBe(callCountAfterError)
  })
})
