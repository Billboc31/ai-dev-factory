import { useState, useEffect, useCallback } from 'react'
import { listProposals, proposeAutoFix, getProposal, startAutoFixLoop, listAutoFixSessions } from '../api/autoFix'

const STATUS_COLOR = {
  idle: 'text-gray-400',
  pending: 'text-yellow-400',
  ready: 'text-green-400',
  rejected: 'text-orange-400',
  running: 'text-yellow-400',
  success: 'text-green-400',
  failed: 'text-red-400',
  error: 'text-red-400',
}

function PatchCard({ patch }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className={`border rounded p-2 text-sm ${patch.valid ? 'border-green-700' : 'border-red-700'}`}>
      <div className="flex items-center justify-between">
        <span className={`font-mono text-xs ${patch.valid ? 'text-green-300' : 'text-red-300'}`}>
          {patch.relative_path}
        </span>
        <span className={`text-xs ml-2 ${patch.valid ? 'text-green-400' : 'text-red-400'}`}>
          {patch.valid ? 'valid' : 'rejected (out-of-scope)'}
        </span>
      </div>
      {patch.valid && (
        <button
          className="text-xs text-blue-400 mt-1"
          onClick={() => setExpanded(v => !v)}
        >
          {expanded ? 'hide content' : 'show content'}
        </button>
      )}
      {expanded && patch.valid && (
        <pre className="mt-2 bg-gray-900 text-gray-200 text-xs p-2 rounded overflow-auto max-h-48">
          {patch.content}
        </pre>
      )}
    </div>
  )
}

function ProposalRow({ proposal, onSelect, selected }) {
  const colorClass = STATUS_COLOR[proposal.status] ?? 'text-gray-400'
  return (
    <tr
      className={`cursor-pointer hover:bg-gray-700 ${selected ? 'bg-gray-700' : ''}`}
      onClick={() => onSelect(proposal)}
    >
      <td className="px-3 py-2 font-mono text-xs text-gray-300">{proposal.proposal_id}</td>
      <td className="px-3 py-2 text-xs text-gray-400">{proposal.sandbox_id ?? '—'}</td>
      <td className="px-3 py-2 text-xs text-gray-400">{proposal.failing_step ?? '—'}</td>
      <td className={`px-3 py-2 text-xs font-medium ${colorClass}`}>{proposal.status}</td>
      <td className="px-3 py-2 text-xs text-gray-500">{proposal.created_at?.slice(0, 19) ?? '—'}</td>
    </tr>
  )
}

function IterationRow({ iter }) {
  const [expanded, setExpanded] = useState(false)
  const colorClass = STATUS_COLOR[iter.status] ?? 'text-gray-400'
  return (
    <div className="border border-gray-700 rounded p-3 space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">
          Iteration {iter.iteration}
          {iter.changed_files?.length > 0 && (
            <span className="ml-2 text-blue-400">{iter.changed_files.length} file(s) patched</span>
          )}
        </span>
        <span className={`text-xs font-medium ${colorClass}`}>{iter.status}</span>
      </div>
      {iter.reasoning && <p className="text-xs text-gray-500 italic">{iter.reasoning}</p>}
      {iter.error && <p className="text-xs text-red-400">{iter.error}</p>}
      {iter.changed_files?.length > 0 && (
        <div className="text-xs text-gray-500">
          {iter.changed_files.map(f => <div key={f} className="font-mono">{f}</div>)}
        </div>
      )}
      {iter.log_lines?.length > 0 && (
        <>
          <button className="text-xs text-blue-400" onClick={() => setExpanded(v => !v)}>
            {expanded ? 'hide logs' : `show logs (${iter.log_lines.length} lines)`}
          </button>
          {expanded && (
            <pre className="bg-gray-900 text-gray-300 text-xs p-2 rounded overflow-auto max-h-48">
              {iter.log_lines.join('\n')}
            </pre>
          )}
        </>
      )}
    </div>
  )
}

function SessionRow({ session, onSelect, selected }) {
  const colorClass = STATUS_COLOR[session.status] ?? 'text-gray-400'
  return (
    <tr
      className={`cursor-pointer hover:bg-gray-700 ${selected ? 'bg-gray-700' : ''}`}
      onClick={() => onSelect(session)}
    >
      <td className="px-3 py-2 font-mono text-xs text-gray-300">{session.session_id}</td>
      <td className="px-3 py-2 text-xs text-gray-400">{session.sandbox_id ?? '—'}</td>
      <td className="px-3 py-2 text-xs text-gray-400 text-center">
        {session.current_iteration} / {session.max_retries}
      </td>
      <td className={`px-3 py-2 text-xs font-medium ${colorClass}`}>{session.status}</td>
      <td className="px-3 py-2 text-xs text-gray-500">{session.created_at?.slice(0, 19) ?? '—'}</td>
    </tr>
  )
}

export default function AutoFixPanel({ projectId }) {
  const [proposals, setProposals] = useState([])
  const [selected, setSelected] = useState(null)
  const [polling, setPolling] = useState(false)
  const [sandboxId, setSandboxId] = useState('')
  const [failingStep, setFailingStep] = useState('')
  const [proposing, setProposing] = useState(false)
  const [error, setError] = useState(null)

  // Loop state
  const [sessions, setSessions] = useState([])
  const [selectedSession, setSelectedSession] = useState(null)
  const [loopExecCmd, setLoopExecCmd] = useState('')
  const [loopSandboxId, setLoopSandboxId] = useState('')
  const [loopMaxRetries, setLoopMaxRetries] = useState('3')
  const [loopFailingStep, setLoopFailingStep] = useState('')
  const [startingLoop, setStartingLoop] = useState(false)
  const [loopError, setLoopError] = useState(null)

  const refresh = useCallback(async () => {
    if (!projectId) return
    try {
      const { data } = await listProposals(projectId)
      setProposals(data.proposals ?? [])
      if (selected) {
        const updated = (data.proposals ?? []).find(p => p.proposal_id === selected.proposal_id)
        if (updated) setSelected(updated)
      }
    } catch {
      // silently ignore polling errors
    }
  }, [projectId, selected])

  const refreshSessions = useCallback(async () => {
    if (!projectId) return
    try {
      const { data } = await listAutoFixSessions(projectId)
      setSessions(data.sessions ?? [])
      if (selectedSession) {
        const updated = (data.sessions ?? []).find(s => s.session_id === selectedSession.session_id)
        if (updated) setSelectedSession(updated)
      }
    } catch {
      // silently ignore polling errors
    }
  }, [projectId, selectedSession])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 4000)
    return () => clearInterval(id)
  }, [refresh])

  useEffect(() => {
    refreshSessions()
    const id = setInterval(refreshSessions, 4000)
    return () => clearInterval(id)
  }, [refreshSessions])

  const hasPending = proposals.some(p => p.status === 'pending')
  useEffect(() => {
    setPolling(hasPending)
  }, [hasPending])

  async function handlePropose() {
    if (!sandboxId.trim()) return
    setProposing(true)
    setError(null)
    try {
      await proposeAutoFix(projectId, sandboxId.trim(), failingStep.trim() || null)
      await refresh()
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message ?? 'request failed')
    } finally {
      setProposing(false)
    }
  }

  async function handleStartLoop() {
    if (!loopExecCmd.trim()) return
    setStartingLoop(true)
    setLoopError(null)
    try {
      await startAutoFixLoop(projectId, {
        execCmd: loopExecCmd.trim(),
        sandboxId: loopSandboxId.trim() || null,
        maxRetries: parseInt(loopMaxRetries, 10) || 3,
        failingStep: loopFailingStep.trim() || null,
      })
      await refreshSessions()
    } catch (e) {
      setLoopError(e?.response?.data?.detail ?? e.message ?? 'request failed')
    } finally {
      setStartingLoop(false)
    }
  }

  if (!projectId) {
    return <p className="text-gray-400 text-sm">Select a project to view auto-fix proposals.</p>
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Auto-Fix Proposals</h2>
        {polling && (
          <span className="text-xs text-yellow-400 animate-pulse">polling…</span>
        )}
      </div>

      {/* Request panel */}
      <div className="bg-gray-800 rounded p-4 space-y-3">
        <p className="text-xs text-gray-400">Propose a fix for a failed sandbox run.</p>
        <div className="flex gap-2">
          <input
            className="flex-1 bg-gray-700 text-gray-200 text-sm rounded px-2 py-1 border border-gray-600 focus:outline-none"
            placeholder="sandbox_id"
            value={sandboxId}
            onChange={e => setSandboxId(e.target.value)}
          />
          <input
            className="flex-1 bg-gray-700 text-gray-200 text-sm rounded px-2 py-1 border border-gray-600 focus:outline-none"
            placeholder="failing_step (optional)"
            value={failingStep}
            onChange={e => setFailingStep(e.target.value)}
          />
          <button
            className="bg-blue-600 hover:bg-blue-500 text-white text-sm px-3 py-1 rounded disabled:opacity-50"
            onClick={handlePropose}
            disabled={proposing || !sandboxId.trim()}
          >
            {proposing ? 'Requesting…' : 'Propose Fix'}
          </button>
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>

      {/* Proposal list */}
      {proposals.length === 0 ? (
        <p className="text-gray-500 text-sm">No proposals yet.</p>
      ) : (
        <div className="overflow-auto rounded border border-gray-700">
          <table className="w-full text-left">
            <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
              <tr>
                <th className="px-3 py-2">ID</th>
                <th className="px-3 py-2">Sandbox</th>
                <th className="px-3 py-2">Failing Step</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700 bg-gray-900">
              {proposals.map(p => (
                <ProposalRow
                  key={p.proposal_id}
                  proposal={p}
                  onSelect={setSelected}
                  selected={selected?.proposal_id === p.proposal_id}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Proposal detail */}
      {selected && (
        <div className="bg-gray-800 rounded p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-white">
              Proposal <span className="font-mono text-gray-400">{selected.proposal_id}</span>
            </h3>
            <button className="text-xs text-gray-500 hover:text-gray-300" onClick={() => setSelected(null)}>
              close
            </button>
          </div>
          <div className="text-xs text-gray-400 space-y-1">
            <p>Status: <span className={`font-medium ${STATUS_COLOR[selected.status] ?? 'text-gray-300'}`}>{selected.status}</span></p>
            {selected.error && <p className="text-red-400">Error: {selected.error}</p>}
            {selected.status === 'pending' && (
              <p className="text-yellow-400 animate-pulse">AI is analyzing the failure…</p>
            )}
          </div>
          {selected.patches && selected.patches.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-gray-400 font-medium">
                Patches ({selected.patches.length}) — read-only preview, no files are modified
              </p>
              {selected.patches.map((p, i) => (
                <PatchCard key={i} patch={p} />
              ))}
            </div>
          )}
          {selected.patches && selected.patches.length === 0 && selected.status === 'ready' && (
            <p className="text-xs text-gray-400">AI proposed no changes.</p>
          )}
        </div>
      )}

      {/* ── Auto-Fix Loop ───────────────────────────────────────────── */}
      <div className="border-t border-gray-700 pt-4 space-y-4">
        <h2 className="text-lg font-semibold text-white">Auto-Fix Loop</h2>

        {/* Loop start form */}
        <div className="bg-gray-800 rounded p-4 space-y-3">
          <p className="text-xs text-gray-400">
            Start an automated fix loop — the AI will apply patches and rerun validation until success or max retries.
          </p>
          <div className="flex gap-2 flex-wrap">
            <input
              className="flex-1 min-w-40 bg-gray-700 text-gray-200 text-sm rounded px-2 py-1 border border-gray-600 focus:outline-none"
              placeholder="exec_cmd (required, e.g. claude --print)"
              value={loopExecCmd}
              onChange={e => setLoopExecCmd(e.target.value)}
            />
            <input
              className="w-32 bg-gray-700 text-gray-200 text-sm rounded px-2 py-1 border border-gray-600 focus:outline-none"
              placeholder="sandbox_id"
              value={loopSandboxId}
              onChange={e => setLoopSandboxId(e.target.value)}
            />
            <input
              className="w-24 bg-gray-700 text-gray-200 text-sm rounded px-2 py-1 border border-gray-600 focus:outline-none"
              placeholder="failing_step"
              value={loopFailingStep}
              onChange={e => setLoopFailingStep(e.target.value)}
            />
            <input
              className="w-20 bg-gray-700 text-gray-200 text-sm rounded px-2 py-1 border border-gray-600 focus:outline-none"
              placeholder="max retries"
              type="number"
              min="1"
              max="10"
              value={loopMaxRetries}
              onChange={e => setLoopMaxRetries(e.target.value)}
            />
            <button
              className="bg-purple-600 hover:bg-purple-500 text-white text-sm px-3 py-1 rounded disabled:opacity-50"
              onClick={handleStartLoop}
              disabled={startingLoop || !loopExecCmd.trim()}
            >
              {startingLoop ? 'Starting…' : 'Start Loop'}
            </button>
          </div>
          {loopError && <p className="text-xs text-red-400">{loopError}</p>}
        </div>

        {/* Session list */}
        {sessions.length === 0 ? (
          <p className="text-gray-500 text-sm">No loop sessions yet.</p>
        ) : (
          <div className="overflow-auto rounded border border-gray-700">
            <table className="w-full text-left">
              <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
                <tr>
                  <th className="px-3 py-2">Session</th>
                  <th className="px-3 py-2">Sandbox</th>
                  <th className="px-3 py-2 text-center">Iter / Max</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Started</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700 bg-gray-900">
                {sessions.map(s => (
                  <SessionRow
                    key={s.session_id}
                    session={s}
                    onSelect={setSelectedSession}
                    selected={selectedSession?.session_id === s.session_id}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Session detail */}
        {selectedSession && (
          <div className="bg-gray-800 rounded p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-white">
                Session <span className="font-mono text-gray-400">{selectedSession.session_id}</span>
              </h3>
              <button
                className="text-xs text-gray-500 hover:text-gray-300"
                onClick={() => setSelectedSession(null)}
              >
                close
              </button>
            </div>
            <div className="text-xs text-gray-400 space-y-1">
              <p>
                Status:{' '}
                <span className={`font-medium ${STATUS_COLOR[selectedSession.status] ?? 'text-gray-300'}`}>
                  {selectedSession.status}
                </span>
              </p>
              <p>
                Iteration: {selectedSession.current_iteration} / {selectedSession.max_retries}
              </p>
              {selectedSession.error && <p className="text-red-400">Error: {selectedSession.error}</p>}
              {selectedSession.status === 'running' && (
                <p className="text-yellow-400 animate-pulse">Loop running…</p>
              )}
            </div>
            {selectedSession.iterations?.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs text-gray-400 font-medium">
                  Iterations ({selectedSession.iterations.length})
                </p>
                {selectedSession.iterations.map(iter => (
                  <IterationRow key={iter.iteration} iter={iter} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
