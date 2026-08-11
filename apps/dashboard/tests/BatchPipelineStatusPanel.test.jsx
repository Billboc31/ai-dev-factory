import { render, screen, within } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import BatchPipelineStatusPanel from '../src/components/BatchPipelineStatusPanel'

const frozen_blocking = {
  batch_id: 'B001',
  batch_status: 'frozen',
  waiting_summary: 'Waiting on Ticket Intelligence: T002, T003',
  tickets: [
    {
      ticket_id: 'T001',
      title: 'Foundation ticket',
      intelligence_status: 'completed',
      readiness_status: null,
      runtime_state: 'DONE',
      is_blocking: false,
      blocking_reason: null,
    },
    {
      ticket_id: 'T002',
      title: 'Feature A',
      intelligence_status: 'running',
      readiness_status: null,
      runtime_state: 'INIT',
      is_blocking: true,
      blocking_reason: 'Intelligence running',
    },
    {
      ticket_id: 'T003',
      title: 'Feature B',
      intelligence_status: 'queued',
      readiness_status: null,
      runtime_state: null,
      is_blocking: true,
      blocking_reason: 'Intelligence queued',
    },
  ],
}

const frozen_ready = {
  batch_id: 'B002',
  batch_status: 'frozen',
  waiting_summary: 'Ready for dependency analysis',
  tickets: [
    {
      ticket_id: 'T001',
      title: 'Foundation',
      intelligence_status: 'completed',
      readiness_status: null,
      runtime_state: null,
      is_blocking: false,
      blocking_reason: null,
    },
  ],
}

const readiness_blocking = {
  batch_id: 'B003',
  batch_status: 'readiness_running',
  waiting_summary: 'Waiting on readiness: T003, T004',
  tickets: [
    {
      ticket_id: 'T003',
      title: 'Feature A',
      intelligence_status: 'completed',
      readiness_status: 'running',
      runtime_state: 'INIT',
      is_blocking: true,
      blocking_reason: 'Readiness running',
    },
    {
      ticket_id: 'T004',
      title: 'Feature B',
      intelligence_status: 'completed',
      readiness_status: null,
      runtime_state: null,
      is_blocking: true,
      blocking_reason: 'Readiness not started',
    },
  ],
}

const dispatching = {
  batch_id: 'B004',
  batch_status: 'dispatching',
  waiting_summary: 'Dispatching tickets',
  tickets: [
    {
      ticket_id: 'T001',
      title: 'Foundation',
      intelligence_status: 'completed',
      readiness_status: 'completed',
      runtime_state: 'CODING',
      is_blocking: false,
      blocking_reason: null,
    },
    {
      ticket_id: 'T002',
      title: 'Feature A',
      intelligence_status: 'running',
      readiness_status: 'failed',
      runtime_state: null,
      is_blocking: false,
      blocking_reason: null,
    },
  ],
}

describe('BatchPipelineStatusPanel', () => {
  it('case 1: frozen + blocking intelligence → yellow banner, blocking IDs in banner, blocking_reason in table', () => {
    render(<BatchPipelineStatusPanel data={frozen_blocking} />)
    const banner = screen.getByTestId('pipeline-waiting-summary')
    expect(banner).toHaveTextContent('T002')
    expect(banner).toHaveTextContent('T003')
    expect(banner.className).toMatch(/yellow/)

    const rowT002 = screen.getByTestId('pipeline-row-T002')
    expect(rowT002).toHaveTextContent('Intelligence running')

    const rowT003 = screen.getByTestId('pipeline-row-T003')
    expect(rowT003).toHaveTextContent('Intelligence queued')
  })

  it('case 2: frozen + all complete → green banner, no blocking reasons shown', () => {
    render(<BatchPipelineStatusPanel data={frozen_ready} />)
    const banner = screen.getByTestId('pipeline-waiting-summary')
    expect(banner).toHaveTextContent('Ready for dependency analysis')
    expect(banner.className).toMatch(/green/)

    const row = screen.getByTestId('pipeline-row-T001')
    const cells = within(row).getAllByRole('cell')
    const blockingCell = cells[cells.length - 1]
    expect(blockingCell).toHaveTextContent('')
  })

  it('case 3: readiness_running + blocking → yellow banner with ticket IDs', () => {
    render(<BatchPipelineStatusPanel data={readiness_blocking} />)
    const banner = screen.getByTestId('pipeline-waiting-summary')
    expect(banner).toHaveTextContent('Waiting on readiness:')
    expect(banner).toHaveTextContent('T003')
    expect(banner).toHaveTextContent('T004')
    expect(banner.className).toMatch(/yellow/)
  })

  it('case 4: ticket with readiness_status=null renders — not blank', () => {
    render(<BatchPipelineStatusPanel data={readiness_blocking} />)
    const rowT004 = screen.getByTestId('pipeline-row-T004')
    const cells = within(rowT004).getAllByRole('cell')
    // readiness cell is the 4th column (index 3)
    expect(cells[3]).toHaveTextContent('—')
  })

  it('case 5: dispatching batch → all blocking_reason cells empty, banner is gray', () => {
    render(<BatchPipelineStatusPanel data={dispatching} />)
    const banner = screen.getByTestId('pipeline-waiting-summary')
    expect(banner).toHaveTextContent('Dispatching tickets')
    expect(banner.className).not.toMatch(/yellow/)
    expect(banner.className).not.toMatch(/green/)

    for (const tid of ['T001', 'T002']) {
      const row = screen.getByTestId(`pipeline-row-${tid}`)
      const cells = within(row).getAllByRole('cell')
      const blockingCell = cells[cells.length - 1]
      expect(blockingCell).toHaveTextContent('')
    }
  })
})
