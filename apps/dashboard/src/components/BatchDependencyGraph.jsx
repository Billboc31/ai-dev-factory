import { useMemo } from 'react'
import ReactFlow, { Background, Controls, MiniMap } from 'reactflow'
import 'reactflow/dist/style.css'

export const COLOR_KEY_TO_BG = {
  done: 'bg-green-500 border-green-700 text-white',
  running: 'bg-blue-500 border-blue-700 text-white',
  waiting: 'bg-gray-300 border-gray-500 text-gray-900',
  waiting_human: 'bg-orange-400 border-orange-600 text-white',
  failed: 'bg-red-500 border-red-700 text-white',
  selected: 'bg-purple-500 border-purple-700 text-white',
}

export function colorClassForKey(colorKey) {
  return COLOR_KEY_TO_BG[colorKey] || COLOR_KEY_TO_BG.waiting
}

function nodeStyleFor(colorKey) {
  const palette = {
    done: { background: '#22c55e', color: 'white', borderColor: '#15803d' },
    running: { background: '#3b82f6', color: 'white', borderColor: '#1d4ed8' },
    waiting: { background: '#d1d5db', color: '#111827', borderColor: '#6b7280' },
    waiting_human: { background: '#fb923c', color: 'white', borderColor: '#c2410c' },
    failed: { background: '#ef4444', color: 'white', borderColor: '#b91c1c' },
    selected: { background: '#a855f7', color: 'white', borderColor: '#7e22ce' },
  }
  const style = palette[colorKey] || palette.waiting
  return {
    ...style,
    padding: '6px 10px',
    borderRadius: 6,
    border: `2px solid ${style.borderColor}`,
    fontSize: 12,
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
  }
}

function buildLayout(nodes) {
  const xSpacing = 220
  const ySpacing = 80
  const phaseBuckets = new Map()
  nodes.forEach(n => {
    const phase = n.execution_phase == null ? 'unphased' : Number(n.execution_phase)
    if (!phaseBuckets.has(phase)) phaseBuckets.set(phase, [])
    phaseBuckets.get(phase).push(n)
  })
  const ordered = [...phaseBuckets.keys()].sort((a, b) => {
    if (a === 'unphased') return 1
    if (b === 'unphased') return -1
    return a - b
  })
  const positions = new Map()
  ordered.forEach((key, columnIndex) => {
    const bucket = phaseBuckets.get(key)
    bucket.forEach((n, rowIndex) => {
      positions.set(n.id, {
        x: columnIndex * xSpacing,
        y: rowIndex * ySpacing,
      })
    })
  })
  return positions
}

export default function BatchDependencyGraph({ graph }) {
  const flowNodes = useMemo(() => {
    if (!graph?.nodes) return []
    const positions = buildLayout(graph.nodes)
    return graph.nodes.map(n => ({
      id: n.id,
      data: { label: n.label || n.id },
      position: positions.get(n.id) || { x: 0, y: 0 },
      style: nodeStyleFor(n.color_key),
    }))
  }, [graph])

  const flowEdges = useMemo(() => {
    if (!graph?.edges) return []
    return graph.edges.map((edge, idx) => {
      const isConflict = edge.type === 'conflicts_with'
      return {
        id: `e-${idx}-${edge.from}-${edge.to}`,
        source: edge.from,
        target: edge.to,
        animated: edge.type === 'depends_on',
        style: isConflict
          ? { stroke: '#dc2626', strokeDasharray: '4 2' }
          : { stroke: '#1f2937' },
        label: isConflict ? 'conflict' : undefined,
        labelStyle: { fontSize: 10, fill: '#dc2626' },
      }
    })
  }, [graph])

  const showMiniMap = (graph?.nodes?.length || 0) > 20

  if (!graph || !graph.nodes || graph.nodes.length === 0) {
    return (
      <div className="border border-gray-200 rounded p-6 text-center text-sm text-gray-400">
        No dependency graph available for this batch.
      </div>
    )
  }

  return (
    <div
      data-testid="batch-dependency-graph"
      className="border border-gray-200 rounded bg-white"
      style={{ height: 480 }}
    >
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={16} />
        <Controls />
        {showMiniMap && <MiniMap pannable zoomable />}
      </ReactFlow>
    </div>
  )
}
