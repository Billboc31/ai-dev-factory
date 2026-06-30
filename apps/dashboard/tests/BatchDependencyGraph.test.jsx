import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

// Stub reactflow before the component imports it so the test does not need a
// real SVG renderer. We render a marker element so we can still assert that
// the component delegated to reactflow with the expected node/edge counts.
vi.mock('reactflow', async () => {
  const React = await import('react')
  const ReactFlow = ({ nodes = [], edges = [], children }) =>
    React.createElement(
      'div',
      {
        'data-testid': 'react-flow-stub',
        'data-node-count': nodes.length,
        'data-edge-count': edges.length,
      },
      children
    )
  return {
    default: ReactFlow,
    Background: () => null,
    Controls: () => null,
    MiniMap: () => null,
  }
})

// CSS import comes from reactflow; jsdom doesn't parse CSS — stub it.
vi.mock('reactflow/dist/style.css', () => ({}))

import BatchDependencyGraph, {
  colorClassForKey,
  COLOR_KEY_TO_BG,
} from '../src/components/BatchDependencyGraph'

describe('colorClassForKey', () => {
  it('maps each color_key to a distinct class', () => {
    const keys = ['done', 'running', 'waiting', 'waiting_human', 'failed', 'selected']
    const classes = new Set()
    keys.forEach(key => {
      const cls = colorClassForKey(key)
      expect(typeof cls).toBe('string')
      expect(cls.length).toBeGreaterThan(0)
      classes.add(cls)
    })
    expect(classes.size).toBe(keys.length)
  })

  it('falls back to the "waiting" class for unknown keys', () => {
    expect(colorClassForKey('nope')).toBe(COLOR_KEY_TO_BG.waiting)
  })

  it('uses green for done, blue for running, gray for waiting, orange for waiting_human, red for failed, purple for selected', () => {
    expect(colorClassForKey('done')).toMatch(/green/)
    expect(colorClassForKey('running')).toMatch(/blue/)
    expect(colorClassForKey('waiting')).toMatch(/gray/)
    expect(colorClassForKey('waiting_human')).toMatch(/orange/)
    expect(colorClassForKey('failed')).toMatch(/red/)
    expect(colorClassForKey('selected')).toMatch(/purple/)
  })
})

describe('BatchDependencyGraph', () => {
  it('renders empty state when no nodes are provided', () => {
    render(<BatchDependencyGraph graph={{ nodes: [], edges: [] }} />)
    expect(screen.getByText(/no dependency graph/i)).toBeInTheDocument()
  })

  it('forwards nodes and edges to the underlying ReactFlow component', () => {
    const graph = {
      nodes: [
        { id: 'T1', label: 'T1', color_key: 'done', execution_phase: 1 },
        { id: 'T2', label: 'T2', color_key: 'running', execution_phase: 2 },
      ],
      edges: [
        { from: 'T1', to: 'T2', type: 'depends_on' },
      ],
    }
    render(<BatchDependencyGraph graph={graph} />)
    const stub = screen.getByTestId('react-flow-stub')
    expect(stub.getAttribute('data-node-count')).toBe('2')
    expect(stub.getAttribute('data-edge-count')).toBe('1')
  })
})
