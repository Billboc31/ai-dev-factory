import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, it, expect, beforeEach, vi } from 'vitest'

// Stub ReactFlow so the graph render does not require SVG/canvas in jsdom.
vi.mock('reactflow', async () => {
  const React = await import('react')
  const ReactFlow = ({ nodes = [], edges = [] }) =>
    React.createElement(
      'div',
      {
        'data-testid': 'react-flow-stub',
        'data-node-count': nodes.length,
        'data-edge-count': edges.length,
      }
    )
  return {
    default: ReactFlow,
    Background: () => null,
    Controls: () => null,
    MiniMap: () => null,
  }
})
vi.mock('reactflow/dist/style.css', () => ({}))

vi.mock('../src/api/batches')
import * as api from '../src/api/batches'

import BatchDetailPage from '../src/pages/BatchDetailPage'

const BATCH = {
  batch: {
    batch_id: 'B0001',
    status: 'dispatching',
    ticket_count: 2,
    created_at: '2026-06-30T10:00:00Z',
    frozen_at: '2026-06-30T10:05:00Z',
    completed_at: null,
    last_activity_at: '2026-06-30T10:10:00Z',
    dependency_analysis_attempts: 1,
    last_dependency_analysis_error: null,
    progress: { done: 1, running: 1, waiting: 0, failed: 0, total: 2 },
    current_phase: 1,
    freeze_blocked: false,
  },
  tickets: [
    {
      ticket_id: 'T1',
      title: 'first ticket',
      status: 'DONE',
      execution_phase: 1,
      depends_on: [],
      readiness_state: 'ready_candidate',
      dispatcher_state: 'DONE',
    },
    {
      ticket_id: 'T2',
      title: 'second ticket',
      status: 'CODING',
      execution_phase: 2,
      depends_on: ['T1'],
      readiness_state: 'ready_candidate',
      dispatcher_state: 'RUNNING',
    },
  ],
}

const GRAPH = {
  nodes: [
    { id: 'T1', label: 'T1', color_key: 'done', execution_phase: 1 },
    { id: 'T2', label: 'T2', color_key: 'running', execution_phase: 2 },
  ],
  edges: [{ from: 'T1', to: 'T2', type: 'depends_on' }],
}

const PHASES = {
  phases: [
    { phase: 1, tickets: ['T1'] },
    { phase: 2, tickets: ['T2'] },
  ],
}

const INSIGHTS = {
  runnable: ['T2'],
  blocked: [{ ticket_id: 'T3', blocked_by: ['T2'] }],
  conflicts: [{ ticket_id: 'T4', conflicts_with: ['T5'] }],
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/projects/proj-a/dispatcher/batches/B0001']}>
      <Routes>
        <Route
          path="/projects/:projectId/dispatcher/batches/:batchId"
          element={<BatchDetailPage />}
        />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  api.getBatch.mockResolvedValue({ data: BATCH })
  api.getBatchGraph.mockResolvedValue({ data: GRAPH })
  api.getBatchPhases.mockResolvedValue({ data: PHASES })
  api.getBatchInsights.mockResolvedValue({ data: INSIGHTS })
})

describe('BatchDetailPage', () => {
  it('renders the batch header with status and timestamps', async () => {
    renderPage()
    expect(await screen.findByRole('heading', { name: 'B0001' })).toBeInTheDocument()
    expect(screen.getByText('dispatching')).toBeInTheDocument()
  })

  it('renders the ticket table columns', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'B0001' })
    const headers = [
      'Ticket ID',
      'Title',
      'Status',
      'Execution phase',
      'Dependencies',
      'Readiness state',
      'Dispatcher state',
    ]
    for (const header of headers) {
      expect(screen.getByText(header)).toBeInTheDocument()
    }
  })

  it('renders the dependency graph, phases panel, and insights panel', async () => {
    renderPage()
    expect(await screen.findByTestId('batch-dependency-graph')).toBeInTheDocument()
    expect(screen.getByTestId('batch-phases')).toBeInTheDocument()
    expect(screen.getByTestId('batch-insights')).toBeInTheDocument()
  })

  it('exposes a legend element with a class per color_key', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'B0001' })
    const legend = screen.getByLabelText(/color legend/i)
    const keys = ['done', 'running', 'waiting', 'waiting_human', 'failed', 'selected']
    for (const key of keys) {
      const item = legend.querySelector(`[data-color-key="${key}"]`)
      expect(item, `missing legend item for ${key}`).not.toBeNull()
    }
  })

  it('renders insights with blocked-by and conflicts-with labels', async () => {
    renderPage()
    await screen.findByRole('heading', { name: 'B0001' })
    expect(screen.getByText(/blocked by/i)).toBeInTheDocument()
    expect(screen.getByText(/conflicts with/i)).toBeInTheDocument()
  })
})
