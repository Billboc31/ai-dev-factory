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

export default function RuntimeDashboardPage() {
  const [sandboxRuns, setSandboxRuns] = useState([])
  const [proposalRuns, setProposalRuns] = useState([])
  const [health, setHealth] = useState(null)
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

  usePolling(fetchSandboxRuns, 5000)
  usePolling(fetchProposalRuns, 5000)
  usePolling(fetchHealth, 5000)

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

      <Section title="Sandbox Runs">
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
          onClose={handleCloseLogs}
        />
      )}
    </div>
  )
}
