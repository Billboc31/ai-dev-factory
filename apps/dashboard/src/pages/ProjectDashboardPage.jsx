import { useCallback, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getDaemonStatus, startDaemon, stopDaemon, restartDaemon, getBoardData } from '../api/daemon'
import { listProjects, importProject } from '../api/projects'
import { listTickets } from '../api/tickets'
import ActionButton from '../components/ActionButton'
import DaemonActivityFeed from '../components/DaemonActivityFeed'
import RuntimeStatusPanel from '../components/RuntimeStatusPanel'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

function formatUptime(startedAt) {
  if (!startedAt) return null
  const seconds = Math.floor((Date.now() - new Date(startedAt)) / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ${seconds % 60}s`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
}

function DaemonStatusCard({ status }) {
  if (!status) return <p className="text-gray-400 text-sm">Loading…</p>
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span
          className={`w-3 h-3 rounded-full flex-shrink-0 ${status.running ? 'bg-green-400' : 'bg-gray-400'}`}
          aria-hidden="true"
        />
        <span className="text-sm font-semibold">{status.running ? 'Running' : 'Stopped'}</span>
        {status.exit_unexpected && !status.running && (
          <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">crashed</span>
        )}
      </div>
      {status.pid != null && (
        <p className="text-xs text-gray-500">PID: <code className="font-mono">{status.pid}</code></p>
      )}
      {status.started_at && (
        <p className="text-xs text-gray-500">Uptime: {formatUptime(status.started_at)}</p>
      )}
      {status.current_ticket && (
        <p className="text-xs text-gray-500">Ticket: <code className="font-mono">{status.current_ticket}</code></p>
      )}
      {status.last_heartbeat && (
        <p className="text-xs text-gray-400">Last activity: {new Date(status.last_heartbeat).toLocaleTimeString()}</p>
      )}
    </div>
  )
}

function StatCard({ value, label }) {
  return (
    <div className="bg-white border border-gray-200 rounded p-4 text-center">
      <p className="text-3xl font-bold text-gray-900">{value ?? '—'}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  )
}

const REVIEW_NEEDED_STATES = new Set(['PLAN_REVIEW_NEEDED', 'IMPLEMENTATION_REVIEW_NEEDED'])
const TEST_COMPLETE_STATE = 'TEST_COMPLETE'

function AttentionTicketRow({ ticket, projectId }) {
  const isReview = REVIEW_NEEDED_STATES.has(ticket.state)
  const isDone = ticket.state === TEST_COMPLETE_STATE
  return (
    <div className={`flex items-center justify-between px-3 py-2 rounded border text-sm ${
      isDone ? 'border-green-200 bg-green-50' :
      isReview ? 'border-orange-200 bg-orange-50' :
      'border-gray-200 bg-white'
    }`}>
      <Link
        to={`/projects/${projectId}/tickets/${ticket.ticket_id}`}
        className="font-mono font-medium text-blue-600 hover:underline"
      >
        {ticket.ticket_id}
      </Link>
      <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
        isDone ? 'bg-green-100 text-green-800' :
        isReview ? 'bg-orange-100 text-orange-800' :
        'bg-gray-100 text-gray-700'
      }`}>
        {ticket.state}
      </span>
    </div>
  )
}

export default function ProjectDashboardPage() {
  const { projectId } = useParams()
  const [project, setProject] = useState(null)
  const [daemonStatus, setDaemonStatus] = useState(null)
  const [activeTicketCount, setActiveTicketCount] = useState(null)
  const [activeWorkerCount, setActiveWorkerCount] = useState(null)
  const [attentionTickets, setAttentionTickets] = useState([])
  const [error, setError] = useState(null)
  const [hostCommand, setHostCommand] = useState(null)
  const fetchProject = useCallback(() => {
    listProjects()
      .then(res => {
        const p = res.data.find(p => p.name === projectId)
        if (p) setProject(p)
        setError(null)
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [projectId])

  const fetchDaemon = useCallback(() => {
    getDaemonStatus(projectId)
      .then(res => { setDaemonStatus(res.data); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [projectId])

  const fetchCounts = useCallback(() => {
    listTickets(projectId)
      .then(res => {
        const tickets = res.data
        const active = tickets.filter(t => !['COMPLETE', 'FAILED'].includes(t.state)).length
        setActiveTicketCount(active)
        const attention = tickets.filter(t =>
          REVIEW_NEEDED_STATES.has(t.state) || t.state === TEST_COMPLETE_STATE
        )
        setAttentionTickets(attention)
      })
      .catch(() => {})
    getBoardData(projectId)
      .then(res => {
        const running = (res.data.columns || []).find(c => c.id === 'running')
        setActiveWorkerCount(running ? running.items.length : 0)
      })
      .catch(() => {})
  }, [projectId])

  usePolling(fetchProject, 30000, projectId)
  usePolling(fetchDaemon, 10000, projectId)
  usePolling(fetchCounts, 10000, projectId)

  const handleRescan = () => {
    if (!project) return
    importProject(project.root, projectId)
      .then(fetchProject)
      .catch(err => setError(err.response?.data?.detail || err.message))
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{projectId}</h1>
          {project && (
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              {project.stack && (
                <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">{project.stack}</span>
              )}
              {project.root && (
                <span className="text-xs text-gray-500 font-mono truncate max-w-xs" title={project.root}>
                  {project.root}
                </span>
              )}
            </div>
          )}
          {project?.runtime_root && (
            <p className="text-xs text-gray-400 font-mono mt-0.5 truncate max-w-sm" title={project.runtime_root}>
              runtime: {project.runtime_root}
            </p>
          )}
        </div>
        <div className="flex gap-2 flex-wrap justify-end shrink-0">
          <ActionButton
            label="Start daemon"
            action={() => startDaemon(projectId)}
            onSuccess={fetchDaemon}
            onResult={(data) => setHostCommand(data?.host_command || null)}
          />
          <ActionButton
            label="Stop daemon"
            action={() => stopDaemon(projectId)}
            variant="danger"
            onSuccess={fetchDaemon}
          />
          <ActionButton
            label="Restart"
            action={() => restartDaemon(projectId)}
            variant="secondary"
            onSuccess={fetchDaemon}
          />
          <button
            onClick={handleRescan}
            className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded border border-gray-300 transition-colors"
          >
            Re-import
          </button>
          <Link
            to={`/projects/${projectId}/agent-layout`}
            className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded border border-gray-300 transition-colors"
          >
            Agent layout
          </Link>
        </div>
      </div>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      {hostCommand && (
        <div className="bg-yellow-50 border border-yellow-300 rounded p-4">
          <p className="text-sm font-semibold text-yellow-900 mb-1">Run on host:</p>
          <pre className="text-xs font-mono bg-yellow-100 p-2 rounded overflow-x-auto whitespace-pre-wrap break-all">
            {hostCommand}
          </pre>
          <button
            onClick={() => setHostCommand(null)}
            className="text-xs text-yellow-700 hover:underline mt-2"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard value={activeTicketCount} label="Active tickets" />
        <StatCard value={activeWorkerCount} label="Active workers" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="bg-white border border-gray-200 rounded p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Daemon</h2>
          <DaemonStatusCard status={daemonStatus} />
        </div>
        <div className="bg-white border border-gray-200 rounded p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Runtime Status</h2>
          <RuntimeStatusPanel projectId={projectId} />
        </div>
      </div>

      {attentionTickets.length > 0 && (
        <div>
          <div className="flex items-baseline justify-between mb-2">
            <h2 className="text-lg font-semibold">Tickets Needing Attention</h2>
            <Link
              to={`/projects/${projectId}/tickets`}
              className="text-sm text-blue-600 hover:underline"
            >
              View all tickets →
            </Link>
          </div>
          <div className="space-y-1.5">
            {attentionTickets.map(t => (
              <AttentionTicketRow key={t.ticket_id} ticket={t} projectId={projectId} />
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="flex items-baseline justify-between mb-2">
          <h2 className="text-lg font-semibold">Recent Activity</h2>
          <Link
            to={`/projects/${projectId}/tickets`}
            className="text-sm text-blue-600 hover:underline"
          >
            View all tickets →
          </Link>
        </div>
        <DaemonActivityFeed projectId={projectId} />
      </div>
    </div>
  )
}
