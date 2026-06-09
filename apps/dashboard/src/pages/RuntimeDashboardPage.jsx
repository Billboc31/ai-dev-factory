import { useCallback, useState } from 'react'
import * as api from '../api/runtimeDashboard'
import usePolling from '../hooks/usePolling'
import ErrorBanner from '../components/ErrorBanner'
import SandboxRunsTable from '../components/runtime-dashboard/SandboxRunsTable'
import ProposalRunsTable from '../components/runtime-dashboard/ProposalRunsTable'
import RuntimeHealthPanel from '../components/runtime-dashboard/RuntimeHealthPanel'
import LogViewerDrawer from '../components/runtime-dashboard/LogViewerDrawer'

function Section({ title, children }) {
  const [open, setOpen] = useState(true)
  return (
    <div className="bg-white border border-gray-200 rounded">
      <button
        className="w-full flex items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen(o => !o)}
      >
        <h2 className="text-base font-semibold text-gray-800">{title}</h2>
        <span className="text-gray-400 text-sm select-none">{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  )
}

function SandboxTopologyPanel({ overview }) {
  if (!overview) {
    return <p className="text-sm text-gray-400">Loading topology…</p>
  }
  const statusCounts = overview.sandboxes.reduce((acc, s) => {
    acc[s.status] = (acc[s.status] || 0) + 1
    return acc
  }, {})
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-gray-50 border border-gray-200 rounded p-3">
          <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Sandbox Root</p>
          <p className="text-xs font-mono text-gray-700 break-all">{overview.sandbox_root}</p>
        </div>
        <div className="bg-gray-50 border border-gray-200 rounded p-3">
          <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Project</p>
          <p className="text-sm font-medium text-gray-800">{overview.project_name}</p>
        </div>
        <div className="bg-gray-50 border border-gray-200 rounded p-3">
          <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Total Sandboxes</p>
          <p className="text-2xl font-bold text-gray-800">{overview.sandboxes.length}</p>
        </div>
      </div>
      <div className="bg-gray-50 border border-gray-200 rounded p-3">
        <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Project Sandbox Dir</p>
        <p className="text-xs font-mono text-gray-700 break-all">{overview.project_sandbox_dir}</p>
      </div>
      {Object.keys(statusCounts).length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {Object.entries(statusCounts).map(([status, count]) => (
            <span
              key={status}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700"
            >
              {status} <span className="font-bold">{count}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function RuntimeDashboardPage() {
  const [sandboxRuns, setSandboxRuns] = useState([])
  const [proposalRuns, setProposalRuns] = useState([])
  const [health, setHealth] = useState(null)
  const [overview, setOverview] = useState(null)
  const [error, setError] = useState(null)
  const [logSandboxId, setLogSandboxId] = useState(null)

  const fetchSandboxRuns = useCallback(async () => {
    try {
      const res = await api.listSandboxRuns()
      setSandboxRuns(res.data)
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }, [])

  const fetchProposalRuns = useCallback(async () => {
    try {
      const res = await api.listProposalRuns()
      setProposalRuns(res.data)
    } catch {
      // non-critical — proposal runs may not exist
    }
  }, [])

  const fetchHealth = useCallback(async () => {
    try {
      const res = await api.getRuntimeHealth()
      setHealth(res.data)
    } catch {
      // non-critical — health endpoint may be temporarily unavailable
    }
  }, [])

  const fetchOverview = useCallback(async () => {
    try {
      const res = await api.getRuntimeOverview()
      setOverview(res.data)
    } catch {
      // non-critical — overview endpoint may be temporarily unavailable
    }
  }, [])

  usePolling(fetchSandboxRuns, 5000)
  usePolling(fetchProposalRuns, 5000)
  usePolling(fetchHealth, 5000)
  usePolling(fetchOverview, 5000)

  const handleOpenLogs = (sandboxId) => {
    setLogSandboxId(sandboxId)
  }

  const handleCloseLogs = () => {
    setLogSandboxId(null)
  }

  return (
    <div className="max-w-5xl space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Runtime Dashboard</h1>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      <Section title="Sandbox Topology">
        <SandboxTopologyPanel overview={overview} />
      </Section>

      <Section title="Running Environments">
        <SandboxRunsTable
          runs={sandboxRuns}
          onOpenLogs={handleOpenLogs}
          onDeleted={fetchSandboxRuns}
        />
      </Section>

      <Section title="Proposal Runs">
        <ProposalRunsTable
          runs={proposalRuns}
          onDeleted={fetchProposalRuns}
        />
      </Section>

      <Section title="Runtime Health">
        <RuntimeHealthPanel health={health} />
      </Section>

      <Section title="Log Viewer">
        <p className="text-sm text-gray-500">
          Click <span className="font-medium">Open Logs</span> on a sandbox run to tail its output here.
        </p>
      </Section>

      {logSandboxId && (
        <LogViewerDrawer
          sandboxId={logSandboxId}
          failingStep={sandboxRuns.find(r => r.id === logSandboxId)?.failing_step}
          onClose={handleCloseLogs}
        />
      )}
    </div>
  )
}
