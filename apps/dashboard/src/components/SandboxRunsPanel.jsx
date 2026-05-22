import { useCallback, useEffect, useState } from 'react'
import * as deployerApi from '../api/deployer'

const STATE_COLORS = {
  idle: 'bg-gray-100 text-gray-700',
  pending: 'bg-yellow-100 text-yellow-700',
  running: 'bg-yellow-100 text-yellow-700',
  success: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

function LogsModal({ sandboxId, onClose }) {
  const [lines, setLines] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    deployerApi.getSandboxRunLogs(sandboxId, 500)
      .then(res => setLines(res.data.lines))
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [sandboxId])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <span className="text-sm font-semibold text-gray-700 font-mono">{sandboxId}</span>
          <button className="text-gray-400 hover:text-gray-700 text-lg leading-none" onClick={onClose}>✕</button>
        </div>
        <div className="flex-1 overflow-y-auto bg-gray-900 p-4">
          {error && <p className="text-red-400 text-xs">{error}</p>}
          {lines === null && !error && <p className="text-gray-400 text-xs">Loading…</p>}
          {lines !== null && lines.length === 0 && <p className="text-gray-400 text-xs">No logs.</p>}
          {lines !== null && lines.length > 0 && (
            <pre className="text-xs text-green-300 whitespace-pre-wrap">{lines.join('\n')}</pre>
          )}
        </div>
      </div>
    </div>
  )
}

export default function SandboxRunsPanel({ maxRows }) {
  const [runs, setRuns] = useState([])
  const [logsFor, setLogsFor] = useState(null)
  const [cleaning, setCleaning] = useState(null)

  const fetchRuns = useCallback(() => {
    deployerApi.listSandboxRuns()
      .then(res => {
        const all = res.data || []
        setRuns(maxRows != null ? all.slice(-maxRows) : all)
      })
      .catch(() => {})
  }, [maxRows])

  useEffect(() => {
    fetchRuns()
    const id = setInterval(fetchRuns, 10000)
    return () => clearInterval(id)
  }, [fetchRuns])

  const handleCleanup = async (sandboxId) => {
    setCleaning(sandboxId)
    try {
      await deployerApi.cleanupSandboxRun(sandboxId)
      await fetchRuns()
    } catch {
      // ignore
    } finally {
      setCleaning(null)
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded p-4 mt-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-700">Sandbox Runs</h2>
        <button className="text-xs text-blue-600 hover:underline" onClick={fetchRuns}>Refresh</button>
      </div>
      {runs.length === 0 ? (
        <p className="text-xs text-gray-400">No sandbox runs found.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-gray-500 border-b">
                <th className="pb-1 pr-3 font-medium">ID</th>
                <th className="pb-1 pr-3 font-medium">Project</th>
                <th className="pb-1 pr-3 font-medium">State</th>
                <th className="pb-1 pr-3 font-medium">Started</th>
                <th className="pb-1 pr-3 font-medium">Finished</th>
                <th className="pb-1 pr-3 font-medium">Last step</th>
                <th className="pb-1 pr-3 font-medium">Ports</th>
                <th className="pb-1 pr-3 font-medium">Worktree</th>
                <th className="pb-1 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(run => {
                const isRunning = run.state === 'running' || run.state === 'pending'
                const colorClass = STATE_COLORS[run.state] || STATE_COLORS.idle
                const portEntries = run.ports ? Object.entries(run.ports) : []
                return (
                  <tr key={run.sandbox_id} className="border-b last:border-0 align-top">
                    <td className="py-1.5 pr-3 font-mono text-gray-600 max-w-[140px] truncate" title={run.sandbox_id}>
                      {run.sandbox_id}
                    </td>
                    <td className="py-1.5 pr-3 font-mono text-gray-600">{run.project_id}</td>
                    <td className="py-1.5 pr-3">
                      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium ${colorClass}`}>
                        {isRunning && <span className="animate-spin inline-block">↻</span>}
                        {run.state}
                      </span>
                    </td>
                    <td className="py-1.5 pr-3 text-gray-500 whitespace-nowrap">
                      {run.started_at ? run.started_at.replace('T', ' ').replace('Z', '') : '—'}
                    </td>
                    <td className="py-1.5 pr-3 text-gray-500 whitespace-nowrap">
                      {run.finished_at ? run.finished_at.replace('T', ' ').replace('Z', '') : '—'}
                    </td>
                    <td className="py-1.5 pr-3 font-mono text-gray-600">{run.last_step || '—'}</td>
                    <td className="py-1.5 pr-3">
                      {portEntries.length > 0 ? (
                        <div className="flex flex-col gap-0.5">
                          {portEntries.map(([k, v]) => (
                            <span key={k} className="font-mono text-gray-600">
                              <span className="text-gray-400">{k}:</span> {v}
                            </span>
                          ))}
                        </div>
                      ) : '—'}
                    </td>
                    <td className="py-1.5 pr-3 font-mono text-gray-400 max-w-[160px] truncate" title={run.worktree_path}>
                      {run.worktree_path || '—'}
                    </td>
                    <td className="py-1.5">
                      <div className="flex gap-2">
                        <button
                          className="text-blue-600 hover:underline"
                          onClick={() => setLogsFor(run.sandbox_id)}
                        >
                          Logs
                        </button>
                        <button
                          className="text-red-500 hover:underline disabled:opacity-40"
                          disabled={isRunning || cleaning === run.sandbox_id}
                          onClick={() => handleCleanup(run.sandbox_id)}
                        >
                          {cleaning === run.sandbox_id ? '…' : 'Cleanup'}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {logsFor && (
        <LogsModal sandboxId={logsFor} onClose={() => setLogsFor(null)} />
      )}
    </div>
  )
}
