import { render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, beforeEach, vi } from 'vitest'

vi.mock('../src/api/batches')
import * as api from '../src/api/batches'

import BatchesPage from '../src/pages/BatchesPage'

function makeBatch(overrides = {}) {
  return {
    batch_id: 'B0001',
    status: 'collecting',
    ticket_count: 3,
    created_at: '2026-06-30T10:00:00Z',
    last_activity_at: '2026-06-30T10:05:00Z',
    progress: { done: 1, running: 1, waiting: 1, failed: 0, total: 3 },
    current_phase: 1,
    freeze_blocked: false,
    ...overrides,
  }
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/projects/proj-a/dispatcher/batches']}>
      <Routes>
        <Route
          path="/projects/:projectId/dispatcher/batches"
          element={<BatchesPage />}
        />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  api.listBatches.mockResolvedValue({ data: { batches: [] } })
  api.getCurrentNextBatch.mockResolvedValue({ data: { current: null, next: null } })
  api.freezeBatch.mockResolvedValue({ data: { ok: true } })
  api.cancelBatch.mockResolvedValue({ data: { ok: true } })
  api.retryBatchDependencyAnalysis.mockResolvedValue({ data: { ok: true } })
  api.recomputeBatchDependencies.mockResolvedValue({ data: { ok: true } })
})

describe('BatchesPage', () => {
  it('renders the required table columns', async () => {
    renderPage()
    await screen.findByText(/no batches yet/i)
    const headers = [
      'Batch ID',
      'Status',
      'Ticket count',
      'Created at',
      'Last activity',
      'Progress',
      'Current phase',
      'Actions',
    ]
    for (const header of headers) {
      expect(screen.getByText(header)).toBeInTheDocument()
    }
  })

  it('renders one row per batch returned by the API', async () => {
    api.listBatches.mockResolvedValue({
      data: {
        batches: [
          makeBatch({ batch_id: 'B0001', status: 'collecting' }),
          makeBatch({ batch_id: 'B0002', status: 'dispatching' }),
        ],
      },
    })
    renderPage()
    expect(await screen.findByText('B0001')).toBeInTheDocument()
    expect(screen.getByText('B0002')).toBeInTheDocument()
  })

  it('renders the Current batch / Next batch overview', async () => {
    api.getCurrentNextBatch.mockResolvedValue({
      data: {
        current: makeBatch({ batch_id: 'B0001', status: 'dispatching' }),
        next: makeBatch({ batch_id: 'B0002', status: 'collecting' }),
      },
    })
    renderPage()
    expect(await screen.findByText(/current batch/i)).toBeInTheDocument()
    expect(screen.getByText(/next batch/i)).toBeInTheDocument()
    expect(screen.getByText('B0001')).toBeInTheDocument()
    expect(screen.getByText('B0002')).toBeInTheDocument()
  })

  it('disables Force freeze when the batch is not collecting', async () => {
    api.listBatches.mockResolvedValue({
      data: {
        batches: [makeBatch({ batch_id: 'B0001', status: 'dispatching' })],
      },
    })
    renderPage()
    await screen.findByText('B0001')
    expect(screen.getByRole('button', { name: /force freeze/i })).toBeDisabled()
  })

  it('enables Force freeze when status is collecting and calls the API on click', async () => {
    api.listBatches.mockResolvedValue({
      data: {
        batches: [makeBatch({ batch_id: 'B0001', status: 'collecting' })],
      },
    })
    renderPage()
    await screen.findByText('B0001')
    const btn = screen.getByRole('button', { name: /force freeze/i })
    expect(btn).not.toBeDisabled()
    await userEvent.click(btn)
    expect(api.freezeBatch).toHaveBeenCalledWith('proj-a', 'B0001')
  })

  it('disables Retry analysis unless status is dependency_analysis_failed', async () => {
    api.listBatches.mockResolvedValue({
      data: {
        batches: [makeBatch({ batch_id: 'B0001', status: 'collecting' })],
      },
    })
    renderPage()
    await screen.findByText('B0001')
    expect(screen.getByRole('button', { name: /retry analysis/i })).toBeDisabled()
  })

  it('disables Cancel when status is dispatching', async () => {
    api.listBatches.mockResolvedValue({
      data: {
        batches: [makeBatch({ batch_id: 'B0001', status: 'dispatching' })],
      },
    })
    renderPage()
    await screen.findByText('B0001')
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled()
  })

  it('polls the API every 10 seconds', async () => {
    vi.useFakeTimers()
    try {
      api.listBatches.mockResolvedValue({ data: { batches: [] } })
      api.getCurrentNextBatch.mockResolvedValue({
        data: { current: null, next: null },
      })
      render(
        <MemoryRouter initialEntries={['/projects/proj-a/dispatcher/batches']}>
          <Routes>
            <Route
              path="/projects/:projectId/dispatcher/batches"
              element={<BatchesPage />}
            />
          </Routes>
        </MemoryRouter>
      )
      // initial call from mount
      expect(api.listBatches).toHaveBeenCalledTimes(1)
      vi.advanceTimersByTime(10000)
      expect(api.listBatches).toHaveBeenCalledTimes(2)
      vi.advanceTimersByTime(10000)
      expect(api.listBatches).toHaveBeenCalledTimes(3)
    } finally {
      vi.useRealTimers()
    }
  })

  it('surfaces backend 409 errors via the error banner', async () => {
    api.listBatches.mockResolvedValue({
      data: {
        batches: [makeBatch({ batch_id: 'B0001', status: 'collecting' })],
      },
    })
    api.freezeBatch.mockRejectedValue({
      response: { data: { detail: 'batch B0001 cannot be frozen from status=dispatching' } },
    })
    renderPage()
    await screen.findByText('B0001')
    await userEvent.click(screen.getByRole('button', { name: /force freeze/i }))
    expect(
      await screen.findByText(/cannot be frozen from status=dispatching/i)
    ).toBeInTheDocument()
  })
})
