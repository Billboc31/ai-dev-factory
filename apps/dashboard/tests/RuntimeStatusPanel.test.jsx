import { render, screen } from '@testing-library/react'
import RuntimeStatusPanel from '../src/components/RuntimeStatusPanel'
import * as daemonApi from '../src/api/daemon'

vi.mock('../src/api/daemon')

const baseStatus = {
  daemon_online: true,
  workers: [],
  retry_blocked: [],
  intake_queue: [],
  last_action: null,
  last_error: null,
}

describe('RuntimeStatusPanel', () => {
  it('shows "No active workers" when worker list is empty', async () => {
    daemonApi.getRuntimeStatus.mockResolvedValue({ data: baseStatus })
    render(<RuntimeStatusPanel />)
    expect(await screen.findByText(/no active workers/i)).toBeInTheDocument()
  })

  it('shows worker ticket ID when workers are present', async () => {
    daemonApi.getRuntimeStatus.mockResolvedValue({
      data: {
        ...baseStatus,
        workers: [{ ticket_id: 'T042', pid: 9999, state: 'PLAN_RUNNING', worktree_path: null }],
      },
    })
    render(<RuntimeStatusPanel />)
    expect(await screen.findByText('T042')).toBeInTheDocument()
    expect(await screen.findByText('pid:9999')).toBeInTheDocument()
  })

  it('shows retry-blocked ticket with retry count', async () => {
    daemonApi.getRuntimeStatus.mockResolvedValue({
      data: {
        ...baseStatus,
        retry_blocked: [{ ticket_id: 'T010', retry_count: 3, failure_class: 'tool_error', cooldown_until: null }],
      },
    })
    render(<RuntimeStatusPanel />)
    expect(await screen.findByText('T010')).toBeInTheDocument()
    expect(await screen.findByText('×3')).toBeInTheDocument()
  })

  it('shows intake queue entries', async () => {
    daemonApi.getRuntimeStatus.mockResolvedValue({
      data: {
        ...baseStatus,
        intake_queue: [{ issue_number: 85, title: 'Add runtime status panel' }],
      },
    })
    render(<RuntimeStatusPanel />)
    expect(await screen.findByText(/add runtime status panel/i)).toBeInTheDocument()
    expect(await screen.findByText(/#85/)).toBeInTheDocument()
  })

  it('shows error banner and message when API fails', async () => {
    daemonApi.getRuntimeStatus.mockRejectedValue({ message: 'Network Error' })
    render(<RuntimeStatusPanel />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/runtime status unavailable/i)
  })
})
