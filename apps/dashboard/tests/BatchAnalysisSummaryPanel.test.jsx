import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'

import BatchAnalysisSummaryPanel from '../src/components/BatchAnalysisSummaryPanel'
import RawAnalyzerOutputPanel from '../src/components/RawAnalyzerOutputPanel'

const FULL_SUMMARY = {
  strategy: 'Foundation first, then features.',
  foundation_tickets: ['T1', 'T2'],
  bootstrap_tickets: ['T3'],
  important_inferred_dependencies: ['T4 depends on T1'],
  parallel_opportunities: ['T5 and T6 can run in parallel'],
  conflicts_resolved: ['T7 vs T8 resolved by bumping T8'],
  warnings: ['T9 body is thin'],
  generated_at: '2026-07-02T10:00:00Z',
}

describe('BatchAnalysisSummaryPanel', () => {
  it('renders strategy and every non-empty section when the summary is populated', () => {
    render(<BatchAnalysisSummaryPanel summary={FULL_SUMMARY} />)
    expect(screen.getByTestId('batch-analysis-summary')).toBeInTheDocument()
    expect(screen.getByText(/Foundation first, then features/i)).toBeInTheDocument()
    expect(screen.getByText(/Foundation tickets/i)).toBeInTheDocument()
    expect(screen.getByText(/Bootstrap tickets/i)).toBeInTheDocument()
    expect(screen.getByText(/Important inferred dependencies/i)).toBeInTheDocument()
    expect(screen.getByText(/Parallel execution opportunities/i)).toBeInTheDocument()
    expect(screen.getByText(/Conflicts resolved/i)).toBeInTheDocument()
    expect(screen.getByText(/Warnings/i)).toBeInTheDocument()
    expect(screen.getByText('T4 depends on T1')).toBeInTheDocument()
  })

  it('renders the empty fallback when the summary is null', () => {
    render(<BatchAnalysisSummaryPanel summary={null} />)
    expect(screen.getByTestId('analysis-summary-empty')).toHaveTextContent(
      /Analysis not available yet/i,
    )
  })

  it('renders the empty fallback when every field is empty', () => {
    render(
      <BatchAnalysisSummaryPanel
        summary={{
          strategy: null,
          foundation_tickets: [],
          bootstrap_tickets: [],
          important_inferred_dependencies: [],
          parallel_opportunities: [],
          conflicts_resolved: [],
          warnings: [],
        }}
      />,
    )
    expect(screen.getByTestId('analysis-summary-empty')).toBeInTheDocument()
  })
})

describe('RawAnalyzerOutputPanel', () => {
  it('renders a fallback message when raw output is null', () => {
    render(<RawAnalyzerOutputPanel raw={null} />)
    expect(
      screen.getByText(/Raw output not persisted for this batch/i),
    ).toBeInTheDocument()
  })

  it('renders formatted JSON when raw output is present', () => {
    render(
      <RawAnalyzerOutputPanel
        raw={{ parsed: { tickets: [] }, stdout_excerpt: '…' }}
      />,
    )
    const panel = screen.getByTestId('raw-analyzer-output')
    expect(panel).toBeInTheDocument()
    expect(panel).toHaveTextContent(/"tickets": \[\]/)
    expect(screen.getByRole('button', { name: /Copy JSON/i })).toBeInTheDocument()
  })

  it('acknowledges a Copy JSON click', async () => {
    const user = userEvent.setup({
      writeToClipboard: false,
    })
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async () => undefined },
    })
    render(
      <RawAnalyzerOutputPanel raw={{ parsed: { tickets: [] } }} />,
    )
    const button = screen.getByRole('button', { name: /Copy JSON/i })
    await user.click(button)
    expect(button).toHaveTextContent(/Copied/i)
  })
})
