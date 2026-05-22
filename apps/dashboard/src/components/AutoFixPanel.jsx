import { useState, useEffect, useCallback } from 'react'
import { listProposals, proposeAutoFix, getProposal } from '../api/autoFix'

const STATUS_COLOR = {
  idle: 'text-gray-400',
  pending: 'text-yellow-400',
  ready: 'text-green-400',
  rejected: 'text-orange-400',
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

export default function AutoFixPanel({ projectId }) {
  const [proposals, setProposals] = useState([])
  const [selected, setSelected] = useState(null)
  const [polling, setPolling] = useState(false)
  const [sandboxId, setSandboxId] = useState('')
  const [failingStep, setFailingStep] = useState('')
  const [proposing, setProposing] = useState(false)
  const [error, setError] = useState(null)

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

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 4000)
    return () => clearInterval(id)
  }, [refresh])

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
    </div>
  )
}
