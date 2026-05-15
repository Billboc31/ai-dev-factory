import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import * as api from '../api/tickets'
import ActionButton from '../components/ActionButton'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

const TABS = ['overview', 'logs', 'plan', 'review', 'tests', 'artifacts']

const TAB_FETCHERS = {
  overview: (id) => api.getTicketState(id),
  logs: (id) => api.getTicketLogs(id),
  plan: (id) => api.getTicketPlan(id),
  review: (id) => api.getTicketReview(id),
  tests: (id) => api.getTicketTests(id),
  artifacts: (id) => api.getTicketArtifacts(id)
}

function renderContent(content) {
  if (content === undefined || content === null) return ''
  if (typeof content === 'string') return content
  return JSON.stringify(content, null, 2)
}

export default function TicketDetailPage() {
  const { id } = useParams()
  const [ticket, setTicket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('overview')
  const [tabContent, setTabContent] = useState({})
  const [tabLoading, setTabLoading] = useState(false)
  const prevStateRef = useRef(null)
  const activeTabRef = useRef(tab)

  // Reset on ticket navigation
  useEffect(() => {
    setLoading(true)
    setTicket(null)
    setError(null)
    setTab('overview')
    setTabContent({})
    prevStateRef.current = null
  }, [id])

  useEffect(() => { activeTabRef.current = tab }, [tab])

  const fetchTicket = useCallback(() => {
    api.getTicket(id)
      .then(res => {
        const newTicket = res.data
        if (prevStateRef.current !== null && prevStateRef.current !== newTicket.state) {
          setTabContent({})
        } else if (activeTabRef.current === 'logs') {
          setTabContent(prev => { const n = { ...prev }; delete n.logs; return n })
        }
        prevStateRef.current = newTicket.state
        setTicket(newTicket)
        setError(null)
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [id])

  // Restart polling and fetch immediately when id changes
  usePolling(fetchTicket, 5000, id)

  useEffect(() => {
    if (tabContent[tab] !== undefined) return

    const fetcher = TAB_FETCHERS[tab]
    if (!fetcher) return

    setTabLoading(true)
    fetcher(id)
      .then(res => setTabContent(prev => ({ ...prev, [tab]: res.data })))
      .catch(err => setTabContent(prev => ({
        ...prev,
        [tab]: `Error: ${err.response?.data?.detail || err.message}`
      })))
      .finally(() => setTabLoading(false))
  }, [tab, id, tabContent])

  const refreshTicket = useCallback(() => {
    prevStateRef.current = null
    setTabContent({})
    api.getTicket(id)
      .then(res => setTicket(res.data))
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [id])

  if (loading) return <p className="text-gray-500">Loading…</p>

  if (!ticket && error) {
    return (
      <div>
        <Link to="/" className="text-blue-600 hover:underline text-sm">← Back</Link>
        <div className="mt-4"><ErrorBanner message={error} /></div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl">
      <Link to="/" className="text-blue-600 hover:underline text-sm">← Back to Tickets</Link>

      <div className="mt-4 mb-6 flex items-center gap-3">
        <h1 className="text-2xl font-bold font-mono">{id}</h1>
        {ticket?.state && (
          <span className="px-2 py-1 rounded bg-blue-100 text-blue-800 text-sm font-medium">
            {ticket.state}
          </span>
        )}
        {ticket?.branch && (
          <span className="text-xs text-gray-500 font-mono">{ticket.branch}</span>
        )}
      </div>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="flex border-b border-gray-200 mb-4">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors ${
              tab === t
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mb-6 min-h-32">
        {tabLoading
          ? <p className="text-gray-500 text-sm">Loading…</p>
          : <pre className="bg-white border border-gray-200 rounded p-4 text-xs overflow-auto whitespace-pre-wrap max-h-96">
              {renderContent(tabContent[tab]) || 'No content available.'}
            </pre>
        }
      </div>

      <div className="bg-white border border-gray-200 rounded p-4 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Workflow</h2>
          <div className="flex flex-wrap gap-2">
            <ActionButton label="Run Next" action={() => api.runNextStep(id)} onSuccess={refreshTicket} />
            <ActionButton label="Approve Plan" action={() => api.approvePlan(id)} variant="secondary" onSuccess={refreshTicket} />
            <ActionButton label="Request Plan Fix" action={() => api.requestPlanFix(id)} variant="danger" onSuccess={refreshTicket} />
            <ActionButton label="Approve Implementation" action={() => api.approveImplementation(id)} variant="secondary" onSuccess={refreshTicket} />
            <ActionButton label="Request Impl Fix" action={() => api.requestImplementationFix(id)} variant="danger" onSuccess={refreshTicket} />
          </div>
        </div>
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Git / Runtime</h2>
          <div className="flex flex-wrap gap-2">
            <ActionButton label="Commit" action={() => api.commitChanges(id)} variant="secondary" onSuccess={refreshTicket} />
            <ActionButton label="Push" action={() => api.pushChanges(id)} variant="secondary" onSuccess={refreshTicket} />
            <ActionButton label="Checkpoint" action={() => api.createCheckpoint(id)} variant="secondary" onSuccess={refreshTicket} />
            <ActionButton label="Archive daemon" action={() => api.archiveDaemon(id)} variant="danger" onSuccess={refreshTicket} />
          </div>
        </div>
      </div>
    </div>
  )
}
