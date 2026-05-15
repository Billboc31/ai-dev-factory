import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('axios', () => ({
  default: {
    create: () => ({ get: mockGet, post: mockPost })
  }
}))

const { listTickets, getTicket, getTicketLogs, runNextStep, approvePlan, requestPlanFix,
  approveImplementation, requestImplementationFix, commitChanges, pushChanges, createCheckpoint
} = await import('../src/api/tickets')

const { getDaemonStatus, startDaemon, stopDaemon, restartDaemon } = await import('../src/api/daemon')

beforeEach(() => {
  vi.clearAllMocks()
  mockGet.mockResolvedValue({ data: {} })
  mockPost.mockResolvedValue({ data: { ok: true, message: 'ok' } })
})

describe('tickets API', () => {
  it('listTickets calls GET /tickets', async () => {
    await listTickets()
    expect(mockGet).toHaveBeenCalledWith('/tickets')
  })

  it('getTicket calls GET /tickets/{id}', async () => {
    await getTicket('T028')
    expect(mockGet).toHaveBeenCalledWith('/tickets/T028')
  })

  it('getTicketLogs calls GET /tickets/{id}/logs', async () => {
    await getTicketLogs('T028')
    expect(mockGet).toHaveBeenCalledWith('/tickets/T028/logs')
  })

  it('runNextStep calls POST /tickets/{id}/run-next', async () => {
    await runNextStep('T028')
    expect(mockPost).toHaveBeenCalledWith('/tickets/T028/run-next')
  })

  it('approvePlan calls POST /tickets/{id}/approve-plan', async () => {
    await approvePlan('T028')
    expect(mockPost).toHaveBeenCalledWith('/tickets/T028/approve-plan')
  })

  it('requestPlanFix calls POST /tickets/{id}/request-plan-fix', async () => {
    await requestPlanFix('T028')
    expect(mockPost).toHaveBeenCalledWith('/tickets/T028/request-plan-fix')
  })

  it('approveImplementation calls POST /tickets/{id}/approve-implementation', async () => {
    await approveImplementation('T028')
    expect(mockPost).toHaveBeenCalledWith('/tickets/T028/approve-implementation')
  })

  it('requestImplementationFix calls POST /tickets/{id}/request-implementation-fix', async () => {
    await requestImplementationFix('T028')
    expect(mockPost).toHaveBeenCalledWith('/tickets/T028/request-implementation-fix')
  })

  it('commitChanges calls POST /tickets/{id}/commit', async () => {
    await commitChanges('T028')
    expect(mockPost).toHaveBeenCalledWith('/tickets/T028/commit')
  })

  it('pushChanges calls POST /tickets/{id}/push', async () => {
    await pushChanges('T028')
    expect(mockPost).toHaveBeenCalledWith('/tickets/T028/push')
  })

  it('createCheckpoint calls POST /tickets/{id}/checkpoint', async () => {
    await createCheckpoint('T028')
    expect(mockPost).toHaveBeenCalledWith('/tickets/T028/checkpoint')
  })

  it('propagates API errors to the caller', async () => {
    mockGet.mockRejectedValue(new Error('Network Error'))
    await expect(listTickets()).rejects.toThrow('Network Error')
  })
})

describe('daemon API', () => {
  it('getDaemonStatus calls GET /daemon/status', async () => {
    await getDaemonStatus()
    expect(mockGet).toHaveBeenCalledWith('/daemon/status')
  })

  it('startDaemon calls POST /daemon/start', async () => {
    await startDaemon()
    expect(mockPost).toHaveBeenCalledWith('/daemon/start')
  })

  it('stopDaemon calls POST /daemon/stop', async () => {
    await stopDaemon()
    expect(mockPost).toHaveBeenCalledWith('/daemon/stop')
  })

  it('restartDaemon calls POST /daemon/restart', async () => {
    await restartDaemon()
    expect(mockPost).toHaveBeenCalledWith('/daemon/restart')
  })

  it('propagates API errors to the caller', async () => {
    mockPost.mockRejectedValue({ response: { data: { detail: 'Daemon error' } } })
    await expect(startDaemon()).rejects.toMatchObject({ response: { data: { detail: 'Daemon error' } } })
  })
})
