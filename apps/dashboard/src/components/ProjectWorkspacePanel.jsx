import { useState, useEffect, useRef } from 'react'
import { Rnd } from 'react-rnd'
import { postWorkspaceMessage, confirmWorkspaceAction, confirmWorkspaceIssue, getDeploymentStatus } from '../api/workspace'

const STAGE_LABELS = {
  PULLING: 'Pulling…',
  BUILDING_backend: 'Building backend…',
  BUILDING_frontend: 'Building frontend…',
  VERIFYING: 'Verifying…',
  SUCCEEDED: 'Succeeded',
  FAILED: 'Failed',
}

const MIN_WIDTH = 280
const MIN_HEIGHT = 400

function FloatIcon() {
  return (
    <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <rect x="1" y="2" width="10" height="8" rx="1" />
      <line x1="1" y1="5" x2="11" y2="5" />
    </svg>
  )
}

function DockLeftIcon() {
  return (
    <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <rect x="1" y="1" width="10" height="10" rx="1" />
      <line x1="4" y1="1" x2="4" y2="11" />
    </svg>
  )
}

function DockRightIcon() {
  return (
    <svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
      <rect x="1" y="1" width="10" height="10" rx="1" />
      <line x1="8" y1="1" x2="8" y2="11" />
    </svg>
  )
}

const RECOVERY_STAGE_COLORS = {
  DIAGNOSING: 'bg-gray-200 text-gray-700',
  PLAN_READY: 'bg-blue-200 text-blue-700',
  AWAITING_CONFIRMATION: 'bg-yellow-200 text-yellow-800',
  APPLYING_FIX: 'bg-orange-200 text-orange-700',
  RETRYING_STAGE: 'bg-orange-200 text-orange-700',
  VERIFYING: 'bg-blue-200 text-blue-700',
  RECOVERED: 'bg-green-200 text-green-700',
  NEEDS_USER_INPUT: 'bg-yellow-200 text-yellow-800',
  BUG_REPORTED: 'bg-purple-200 text-purple-700',
  FAILED: 'bg-red-200 text-red-700',
}

function RecoveryStageIndicator({ stage }) {
  if (!stage) return null
  const colors = RECOVERY_STAGE_COLORS[stage] || 'bg-gray-200 text-gray-700'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-mono font-medium ${colors}`}>
      {stage}
    </span>
  )
}

function RecoveryReportCard({ report }) {
  if (!report) return null
  return (
    <details className="mt-2 text-xs">
      <summary className="cursor-pointer font-medium text-gray-700">Recovery Report</summary>
      <div className="mt-1 space-y-1 pl-2 border-l-2 border-gray-200">
        <p><span className="font-medium">Root cause:</span> {report.root_cause}</p>
        {report.new_ticket_state && (
          <p><span className="font-medium">New state:</span> {report.new_ticket_state}</p>
        )}
        {report.ops_performed?.length > 0 && (
          <div>
            <p className="font-medium">Operations:</p>
            <ul className="pl-2 space-y-0.5">
              {report.ops_performed.map((op, i) => (
                <li key={i} className={op.success ? 'text-green-700' : 'text-red-600'}>
                  {op.success ? '✓' : '✗'} <code>{op.op_name}</code>: {op.detail}
                </li>
              ))}
            </ul>
          </div>
        )}
        {report.bug_issue_url && (
          <p>
            <span className="font-medium">Bug issue: </span>
            <a
              href={report.bug_issue_url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline text-purple-700 break-all"
            >
              {report.bug_issue_url}
            </a>
          </p>
        )}
        {report.error && (
          <p className="text-red-600"><span className="font-medium">Error:</span> {report.error}</p>
        )}
      </div>
    </details>
  )
}

function RecoveryConfirmCard({ message, onConfirm, loading }) {
  const action = message.proposedAction
  if (!action || action.capability !== 'recover_ticket') return null
  if (message.confirmed) {
    return (
      <div className="mt-2 space-y-1">
        <div className="flex items-center gap-2">
          <RecoveryStageIndicator stage={message.recoveryStage} />
        </div>
        <RecoveryReportCard report={message.recoveryReport} />
        {message.confirmError && (
          <p className="text-red-600 text-xs">{message.confirmError}</p>
        )}
      </div>
    )
  }
  return (
    <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
      <div className="flex items-center gap-2 mb-1">
        <p className="font-medium text-yellow-800">Recovery plan</p>
        <RecoveryStageIndicator stage="PLAN_READY" />
      </div>
      <p className="text-yellow-700 mb-1">
        Ticket: <code>{action.ticket_id}</code> &mdash; Blocker: <code>{action.blocker_class}</code>
      </p>
      {action.operations?.length > 0 ? (
        <table className="w-full text-xs border-collapse mb-2">
          <thead>
            <tr className="text-left text-yellow-900 border-b border-yellow-200">
              <th className="pr-2 py-0.5">Operation</th>
              <th className="pr-2 py-0.5">Risk</th>
              <th className="py-0.5">Description</th>
            </tr>
          </thead>
          <tbody>
            {action.operations.map((op, i) => (
              <tr key={i} className="border-b border-yellow-100">
                <td className="pr-2 py-0.5 font-mono">{op.name}</td>
                <td className={`pr-2 py-0.5 font-medium ${
                  op.risk_level === 'HIGH' ? 'text-red-600' :
                  op.risk_level === 'MEDIUM' ? 'text-orange-600' : 'text-green-600'
                }`}>{op.risk_level}</td>
                <td className="py-0.5 text-yellow-700">{op.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="mb-2 p-2 bg-yellow-100 border border-yellow-300 rounded text-yellow-800 text-xs">
          <p className="font-semibold mb-0.5">Human action required</p>
          {action.blocker_class === 'MISSING_APPROVAL' && (
            <p>This ticket is waiting for a human review or approval. Check the PR or the ticket artifacts for the pending approval gate, then return here to retry.</p>
          )}
          {action.blocker_class === 'USER_DECISION_REQUIRED' && (
            <p>Recovery cannot proceed automatically. A product or scope decision is needed from you before the pipeline can continue.</p>
          )}
          {action.blocker_class !== 'MISSING_APPROVAL' && action.blocker_class !== 'USER_DECISION_REQUIRED' && (
            <p>No automated operations are available for this blocker type (<code>{action.blocker_class}</code>). Manual intervention is required.</p>
          )}
        </div>
      )}
      {message.confirmError && (
        <p className="text-red-600 mb-1">{message.confirmError}</p>
      )}
      {action.operations?.length > 0 && (
        <button
          onClick={() => onConfirm(message)}
          disabled={loading}
          className="px-3 py-1 bg-yellow-500 hover:bg-yellow-600 text-white rounded text-xs disabled:opacity-50"
        >
          Confirm Recovery
        </button>
      )}
    </div>
  )
}

function ActionConfirmCard({ message, onConfirm, loading }) {
  if (!message.proposedAction) return null
  if (message.proposedAction.capability === 'recover_ticket') return null

  const isRedeploy = message.proposedAction.capability === 'redeploy_project'

  // Deployment in progress (background job running)
  if (message.deploymentId && !message.confirmed && !message.confirmError) {
    const stageLabel = STAGE_LABELS[message.deploymentStage] || `${message.deploymentStage}…`
    return (
      <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
        <p className="font-medium text-yellow-800 flex items-center gap-1">
          <span className="inline-block w-3 h-3 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin" />
          {stageLabel}
        </p>
      </div>
    )
  }

  if (message.confirmed) {
    return (
      <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700">
        {message.confirmResult || 'Action executed.'}
      </div>
    )
  }

  return (
    <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs">
      <p className="font-medium text-yellow-800">Proposed action:</p>
      <p className="text-yellow-700 mt-0.5">{message.proposedAction.description}</p>
      {isRedeploy && (
        <table className="mt-1 w-full text-yellow-700 text-xs border-collapse">
          <tbody>
            <tr>
              <td className="pr-2 font-medium">Project</td>
              <td>{message.proposedAction.safe_identifier}</td>
            </tr>
            <tr>
              <td className="pr-2 font-medium">Branch</td>
              <td>{message.proposedAction.configured_branch}</td>
            </tr>
            <tr>
              <td className="pr-2 font-medium">Pull</td>
              <td>{message.proposedAction.pull ? 'Yes' : 'No'}</td>
            </tr>
            <tr>
              <td className="pr-2 font-medium">Components</td>
              <td>{(message.proposedAction.components || []).join(', ')}</td>
            </tr>
            {message.proposedAction.has_dirty_warning === true && (
              <tr>
                <td className="pr-2 font-medium">Local changes</td>
                <td className="text-orange-600 font-semibold">⚠ Uncommitted changes detected</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
      {message.confirmError && (
        <p className="text-red-600 mt-1">{message.confirmError}</p>
      )}
      <button
        onClick={() => onConfirm(message)}
        disabled={loading}
        className="mt-2 px-3 py-1 bg-yellow-500 hover:bg-yellow-600 text-white rounded text-xs disabled:opacity-50"
      >
        Confirm
      </button>
    </div>
  )
}

function IssueConfirmCard({ message, onConfirm, loading }) {
  if (!message.issueDraft) return null
  if (message.confirmed) {
    return (
      <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-700">
        Issue created:{' '}
        <a
          href={message.issueUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="underline break-all"
        >
          {message.issueUrl}
        </a>
      </div>
    )
  }
  return (
    <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs">
      <p className="font-medium text-blue-800">Proposed GitHub issue:</p>
      <p className="font-semibold text-blue-700 mt-0.5">{message.issueDraft.title}</p>
      <p className="text-blue-600 mt-0.5 line-clamp-3 whitespace-pre-line">{message.issueDraft.body}</p>
      {message.confirmError && (
        <p className="text-red-600 mt-1">{message.confirmError}</p>
      )}
      <button
        onClick={() => onConfirm(message)}
        disabled={loading}
        className="mt-2 px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded text-xs disabled:opacity-50"
      >
        Create Issue
      </button>
    </div>
  )
}

export default function ProjectWorkspacePanel({ projectId, isOpen, onClose, layout, setMode, setPosition, setSize }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [viewportWidth, setViewportWidth] = useState(window.innerWidth)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const resizeStartRef = useRef(null)

  const lastMsg = messages[messages.length - 1]
  const showUnblockButton =
    !loading &&
    lastMsg?.role === 'assistant' &&
    (lastMsg?.recoveryStage === 'NEEDS_USER_INPUT' || lastMsg?.recoveryStage === 'FAILED')

  useEffect(() => {
    setMessages([])
    setInput('')
    setError(null)
  }, [projectId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (isOpen) inputRef.current?.focus()
  }, [isOpen])

  useEffect(() => {
    const onResize = () => setViewportWidth(window.innerWidth)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const conversationHistory = messages.map(m => ({ role: m.role, content: m.content }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    const msg = input.trim()
    if (!msg || loading || !projectId) return

    const id = Date.now()
    setMessages(prev => [...prev, { role: 'user', content: msg, id }])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const res = await postWorkspaceMessage(projectId, msg, conversationHistory)
      const data = res.data
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply,
          intent: data.intent,
          proposedAction: data.proposed_action,
          issueDraft: data.issue_draft,
          confirmationRequired: data.confirmation_required,
          recoveryStage: data.recovery_stage || null,
          id: id + 1,
        },
      ])
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmAction = async (msg) => {
    const actionId = msg.proposedAction?.action_id
    if (!actionId) return
    setLoading(true)
    try {
      const res = await confirmWorkspaceAction(projectId, actionId)
      const data = res.data
      const deploymentId = data.deployment_id
      if (deploymentId) {
        setMessages(prev =>
          prev.map(m =>
            m.id === msg.id
              ? { ...m, deploymentId, deploymentStage: 'RUNNING' }
              : m
          )
        )
        setLoading(false)

        const deadline = Date.now() + 15 * 60 * 1000
        const poll = async () => {
          if (Date.now() > deadline) {
            setMessages(prev =>
              prev.map(m =>
                m.id === msg.id
                  ? { ...m, confirmError: 'Deployment timed out — check supervisor logs.' }
                  : m
              )
            )
            return
          }
          try {
            const statusRes = await getDeploymentStatus(projectId, deploymentId)
            const statusData = statusRes.data
            setMessages(prev =>
              prev.map(m =>
                m.id === msg.id
                  ? { ...m, deploymentStage: statusData.stage || statusData.status }
                  : m
              )
            )
            if (statusData.status === 'SUCCEEDED') {
              const sha = statusData.deployed_sha ? ` (sha: ${statusData.deployed_sha})` : ''
              const url = statusData.preview_url ? ` — ${statusData.preview_url}` : ''
              setMessages(prev =>
                prev.map(m =>
                  m.id === msg.id
                    ? { ...m, confirmed: true, confirmResult: `Deployed successfully${sha}${url}` }
                    : m
                )
              )
            } else if (statusData.status === 'FAILED') {
              setMessages(prev =>
                prev.map(m =>
                  m.id === msg.id
                    ? { ...m, confirmError: `${statusData.error_stage}: ${statusData.error_excerpt}` }
                    : m
                )
              )
            } else {
              setTimeout(poll, 2000)
            }
          } catch (err) {
            setMessages(prev =>
              prev.map(m =>
                m.id === msg.id
                  ? { ...m, confirmError: err.response?.data?.detail || err.message }
                  : m
              )
            )
          }
        }
        setTimeout(poll, 2000)
        return
      }
      setMessages(prev =>
        prev.map(m =>
          m.id === msg.id
            ? {
                ...m,
                confirmed: true,
                confirmResult: data.result || 'Done.',
                recoveryReport: data.recovery_report || null,
                recoveryStage: data.recovery_report?.stage || null,
              }
            : m
        )
      )
    } catch (err) {
      setMessages(prev =>
        prev.map(m =>
          m.id === msg.id
            ? { ...m, confirmError: err.response?.data?.detail || err.message }
            : m
        )
      )
    } finally {
      setLoading(false)
    }
  }

  const handleUnblockTicket = () => {
    setInput('Unblock this ticket')
    setTimeout(() => inputRef.current?.focus(), 0)
  }

  const handleConfirmIssue = async (msg) => {
    const draftId = msg.issueDraft?.draft_id
    if (!draftId) return
    setLoading(true)
    try {
      const res = await confirmWorkspaceIssue(projectId, draftId)
      setMessages(prev =>
        prev.map(m =>
          m.id === msg.id
            ? { ...m, confirmed: true, issueUrl: res.data.issue_url }
            : m
        )
      )
    } catch (err) {
      setMessages(prev =>
        prev.map(m =>
          m.id === msg.id
            ? { ...m, confirmError: err.response?.data?.detail || err.message }
            : m
        )
      )
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  const isSmallScreen = viewportWidth < 768

  function handleResizePointerDown(e) {
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    resizeStartRef.current = { startX: e.clientX, startWidth: layout.width }
  }

  function handleResizePointerMove(e) {
    if (!resizeStartRef.current) return
    const { startX, startWidth } = resizeStartRef.current
    const delta = e.clientX - startX
    const sign = layout.mode === 'docked-left' ? 1 : -1
    const maxW = Math.min(800, window.innerWidth - 320)
    const newWidth = Math.max(MIN_WIDTH, Math.min(maxW, startWidth + sign * delta))
    setSize({ width: newWidth, height: layout.height })
  }

  function handleResizePointerUp() {
    resizeStartRef.current = null
  }

  const modeButtonClass = (mode) =>
    `p-1 rounded text-gray-500 hover:text-gray-700 hover:bg-gray-100${layout.mode === mode ? ' ring-2 ring-blue-500' : ''}`

  const header = (
    <div className="flex items-center border-b border-gray-200 bg-gray-50 shrink-0 h-11">
      {!isSmallScreen && (
        <div
          className="ws-drag-handle flex-none flex items-center justify-center gap-0.5 px-1.5 h-full cursor-grab"
          style={{ width: 24 }}
        >
          <span className="block w-0.5 h-4 bg-gray-300 rounded" />
          <span className="block w-0.5 h-4 bg-gray-300 rounded" />
        </div>
      )}
      <span className="text-sm font-semibold text-gray-800 px-2 shrink-0">AI Workspace</span>
      {projectId && (
        <span className="text-xs text-gray-400 truncate max-w-[7rem]" title={projectId}>
          {projectId}
        </span>
      )}
      <div className="flex items-center gap-0.5 ml-auto pr-2" data-no-drag>
        {!isSmallScreen && (
          <>
            <button
              aria-label="Switch to floating window"
              onClick={() => setMode('floating')}
              data-no-drag
              className={modeButtonClass('floating')}
            >
              <FloatIcon />
            </button>
            <button
              aria-label="Dock to left side"
              onClick={() => setMode('docked-left')}
              data-no-drag
              className={modeButtonClass('docked-left')}
            >
              <DockLeftIcon />
            </button>
            <button
              aria-label="Dock to right side"
              onClick={() => setMode('docked-right')}
              data-no-drag
              className={modeButtonClass('docked-right')}
            >
              <DockRightIcon />
            </button>
          </>
        )}
        <button
          onClick={onClose}
          className="p-1 text-gray-400 hover:text-gray-600 text-xl leading-none"
          aria-label="Close workspace"
          data-no-drag
        >
          ×
        </button>
      </div>
    </div>
  )

  const body = (
    <>
      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
        {messages.length === 0 && (
          <p className="text-xs text-gray-400 text-center mt-6 px-2">
            Ask about project status, diagnose tickets, or request a platform action.
          </p>
        )}
        {messages.map(msg => (
          <div key={msg.id} className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className={`max-w-[90%] rounded-lg px-3 py-2 text-sm ${
                msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'
              }`}
            >
              <p className="whitespace-pre-wrap break-words">{msg.content}</p>
              {msg.role === 'assistant' && msg.recoveryStage && !msg.proposedAction && (
                <div className="mt-1">
                  <RecoveryStageIndicator stage={msg.recoveryStage} />
                </div>
              )}
              {msg.role === 'assistant' && msg.intent === 'actionable' && msg.proposedAction?.capability === 'recover_ticket' && (
                <RecoveryConfirmCard
                  message={msg}
                  onConfirm={handleConfirmAction}
                  loading={loading}
                />
              )}
              {msg.role === 'assistant' && msg.intent === 'actionable' && msg.proposedAction?.capability !== 'recover_ticket' && (
                <ActionConfirmCard
                  message={msg}
                  onConfirm={handleConfirmAction}
                  loading={loading}
                />
              )}
              {msg.role === 'assistant' && msg.intent === 'functional_dev' && (
                <IssueConfirmCard message={msg} onConfirm={handleConfirmIssue} loading={loading} />
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-3 py-2 text-xs text-gray-500">
              Thinking…
            </div>
          </div>
        )}
        {showUnblockButton && (
          <div className="flex justify-start">
            <button
              onClick={handleUnblockTicket}
              className="px-3 py-1.5 bg-yellow-100 hover:bg-yellow-200 text-yellow-800 border border-yellow-300 rounded text-xs"
            >
              Unblock ticket
            </button>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="px-3 py-2 bg-red-50 border-t border-red-200 text-xs text-red-600 shrink-0">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="border-t border-gray-200 p-3 flex gap-2 shrink-0">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={projectId ? 'Ask or request an action…' : 'No project selected'}
          disabled={loading || !projectId}
          className="flex-1 text-sm border border-gray-300 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
        />
        <button
          type="submit"
          disabled={loading || !input.trim() || !projectId}
          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded disabled:opacity-50 shrink-0"
        >
          Send
        </button>
      </form>
    </>
  )

  if (isSmallScreen) {
    return (
      <div
        style={{ position: 'fixed', bottom: 0, left: 0, right: 0, height: '60vh', zIndex: 50 }}
        className="bg-white border-t border-gray-200 flex flex-col shadow-lg"
      >
        {header}
        {body}
      </div>
    )
  }

  if (layout.mode === 'floating') {
    return (
      <Rnd
        bounds="window"
        minWidth={MIN_WIDTH}
        minHeight={MIN_HEIGHT}
        position={{ x: layout.x, y: layout.y }}
        size={{ width: layout.width, height: layout.height }}
        onDragStop={(_, d) => setPosition({ x: d.x, y: d.y })}
        onResizeStop={(_, __, ref, ___, pos) => {
          setSize({ width: ref.offsetWidth, height: ref.offsetHeight })
          setPosition(pos)
        }}
        dragHandleClassName="ws-drag-handle"
        cancel="button, input, textarea, [data-no-drag]"
        style={{ position: 'fixed', zIndex: 50 }}
      >
        <div className="h-full bg-white border border-gray-200 flex flex-col rounded shadow-lg overflow-hidden">
          {header}
          {body}
        </div>
      </Rnd>
    )
  }

  const side = layout.mode === 'docked-left' ? 'left' : 'right'
  const isDockedLeft = layout.mode === 'docked-left'

  return (
    <div
      style={{ position: 'fixed', top: 0, [side]: 0, height: '100vh', width: layout.width, zIndex: 40 }}
      className="bg-white border border-gray-200 flex flex-col shadow-lg overflow-hidden"
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          [isDockedLeft ? 'right' : 'left']: 0,
          width: 4,
          height: '100%',
          cursor: 'ew-resize',
          zIndex: 1,
          touchAction: 'none',
        }}
        onPointerDown={handleResizePointerDown}
        onPointerMove={handleResizePointerMove}
        onPointerUp={handleResizePointerUp}
        onPointerCancel={handleResizePointerUp}
      />
      {header}
      {body}
    </div>
  )
}
