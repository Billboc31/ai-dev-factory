import { useState, useEffect, useRef } from 'react'
import { postWorkspaceMessage, confirmWorkspaceAction, confirmWorkspaceIssue } from '../api/workspace'

function ActionConfirmCard({ message, onConfirm, loading }) {
  if (!message.proposedAction) return null
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

export default function ProjectWorkspacePanel({ projectId, isOpen, onClose }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

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
      setMessages(prev =>
        prev.map(m =>
          m.id === msg.id
            ? { ...m, confirmed: true, confirmResult: res.data.result || 'Done.' }
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

  return (
    <div className="w-80 bg-white border-l border-gray-200 flex flex-col shrink-0 h-screen sticky top-0">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50 shrink-0">
        <span className="text-sm font-semibold text-gray-800">AI Workspace</span>
        {projectId && (
          <span className="text-xs text-gray-400 truncate max-w-[8rem]" title={projectId}>
            {projectId}
          </span>
        )}
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-2"
          aria-label="Close workspace"
        >
          ×
        </button>
      </div>

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
              {msg.role === 'assistant' && msg.intent === 'actionable' && (
                <ActionConfirmCard
                  message={msg}
                  onConfirm={handleConfirmAction}
                  loading={loading}
                />
              )}
              {msg.role === 'assistant' && msg.intent === 'functional_dev' && (
                <IssueConfirmCard
                  message={msg}
                  onConfirm={handleConfirmIssue}
                  loading={loading}
                />
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
    </div>
  )
}
