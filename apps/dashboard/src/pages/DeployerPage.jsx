import { useCallback, useEffect, useState } from 'react'
import * as deployerApi from '../api/deployer'
import ActionButton from '../components/ActionButton'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

const STATE_COLORS = {
  idle: 'bg-gray-100 text-gray-700',
  running: 'bg-yellow-100 text-yellow-700',
  success: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

function StatusBadge({ status }) {
  if (!status) return null
  const colorClass = STATE_COLORS[status.state] || STATE_COLORS.idle
  return (
    <div className="bg-white border border-gray-200 rounded p-4 mb-6 space-y-2">
      <div className="flex items-center gap-3">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
          {status.state === 'running' && <span className="animate-spin inline-block">↻</span>}
          {status.state}
        </span>
        <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${status.profile_present ? 'bg-green-400' : 'bg-gray-300'}`} aria-hidden="true" />
        <span className="text-sm text-gray-600">
          {status.profile_present ? 'deploy.yml present' : 'no deploy profile'}
        </span>
      </div>
      {status.error && (
        <p className="text-xs text-red-600">Last error: {status.error}</p>
      )}
    </div>
  )
}

function LogsPanel({ projectId, isRunning }) {
  const [logs, setLogs] = useState([])
  const [open, setOpen] = useState(false)

  const fetchLogs = useCallback(() => {
    deployerApi.getDeployLogs(projectId, 100)
      .then(res => setLogs(res.data.lines))
      .catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (open) fetchLogs()
  }, [open]) // eslint-disable-line

  usePolling(fetchLogs, (open && isRunning) ? 5000 : null, projectId)

  return (
    <div className="mt-4 border border-gray-200 rounded">
      <button
        className="w-full flex items-center justify-between px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        onClick={() => setOpen(o => !o)}
      >
        <span>Deploy Logs</span>
        <span className="text-gray-400">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="p-4 bg-gray-900 rounded-b max-h-80 overflow-y-auto">
          {logs.length === 0 ? (
            <p className="text-gray-400 text-xs">No logs yet.</p>
          ) : (
            <pre className="text-xs text-green-300 whitespace-pre-wrap">{logs.join('\n')}</pre>
          )}
        </div>
      )}
    </div>
  )
}

function AnalysisStatusPanel({ status }) {
  if (!status || status.state === 'idle') return null
  const colorClass = STATE_COLORS[status.state] || STATE_COLORS.idle
  return (
    <div className="bg-white border border-gray-200 rounded p-4 mt-4 space-y-2">
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-gray-700">Analysis</span>
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
          {status.state === 'running' && <span className="animate-spin inline-block">↻</span>}
          {status.state}
        </span>
      </div>
      {status.branch && (
        <p className="text-xs text-gray-600 font-mono">Branch: {status.branch}</p>
      )}
      {status.pr_url && (
        <p className="text-xs">
          <a href={status.pr_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
            View PR →
          </a>
        </p>
      )}
      {status.error && (
        <p className="text-xs text-red-600">Error: {status.error}</p>
      )}
    </div>
  )
}

function AnalysisLogsPanel({ projectId, isRunning }) {
  const [logs, setLogs] = useState([])
  const [open, setOpen] = useState(false)

  const fetchLogs = useCallback(() => {
    deployerApi.getAnalysisLogs(projectId, 100)
      .then(res => setLogs(res.data.lines))
      .catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (open) fetchLogs()
  }, [open]) // eslint-disable-line

  usePolling(fetchLogs, (open && isRunning) ? 5000 : null, projectId)

  return (
    <div className="mt-2 border border-gray-200 rounded">
      <button
        className="w-full flex items-center justify-between px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        onClick={() => setOpen(o => !o)}
      >
        <span>Analysis Logs</span>
        <span className="text-gray-400">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="p-4 bg-gray-900 rounded-b max-h-80 overflow-y-auto">
          {logs.length === 0 ? (
            <p className="text-gray-400 text-xs">No logs yet.</p>
          ) : (
            <pre className="text-xs text-green-300 whitespace-pre-wrap">{logs.join('\n')}</pre>
          )}
        </div>
      )}
    </div>
  )
}

function ScriptsStatusPanel({ status }) {
  if (!status || status.state === 'idle') return null
  const colorClass = STATE_COLORS[status.state] || STATE_COLORS.idle
  return (
    <div className="bg-white border border-gray-200 rounded p-4 mt-4 space-y-2">
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-gray-700">Scripts</span>
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
          {status.state === 'running' && <span className="animate-spin inline-block">↻</span>}
          {status.state}
        </span>
      </div>
      {status.branch && (
        <p className="text-xs text-gray-600 font-mono">Branch: {status.branch}</p>
      )}
      {status.pr_url && (
        <p className="text-xs">
          <a href={status.pr_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
            View PR →
          </a>
        </p>
      )}
      {status.error && (
        <p className="text-xs text-red-600">Error: {status.error}</p>
      )}
    </div>
  )
}

function ScriptsLogsPanel({ projectId, isRunning }) {
  const [logs, setLogs] = useState([])
  const [open, setOpen] = useState(false)

  const fetchLogs = useCallback(() => {
    deployerApi.getScriptsLogs(projectId, 100)
      .then(res => setLogs(res.data.lines))
      .catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (open) fetchLogs()
  }, [open]) // eslint-disable-line

  usePolling(fetchLogs, (open && isRunning) ? 5000 : null, projectId)

  return (
    <div className="mt-2 border border-gray-200 rounded">
      <button
        className="w-full flex items-center justify-between px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        onClick={() => setOpen(o => !o)}
      >
        <span>Scripts Logs</span>
        <span className="text-gray-400">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="p-4 bg-gray-900 rounded-b max-h-80 overflow-y-auto">
          {logs.length === 0 ? (
            <p className="text-gray-400 text-xs">No logs yet.</p>
          ) : (
            <pre className="text-xs text-green-300 whitespace-pre-wrap">{logs.join('\n')}</pre>
          )}
        </div>
      )}
    </div>
  )
}

function ScanResultPanel({ result }) {
  if (!result) return null
  return (
    <div className="bg-white border border-gray-200 rounded p-4 mt-4 space-y-3">
      <h2 className="text-sm font-semibold text-gray-700">Scan Result</h2>
      {result.docker_services.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-1">Docker services</p>
          <ul className="flex flex-wrap gap-1">
            {result.docker_services.map(s => (
              <li key={s} className="px-2 py-0.5 bg-blue-50 border border-blue-200 rounded text-xs font-mono">{s}</li>
            ))}
          </ul>
        </div>
      )}
      {result.required_tools.length > 0 && (
        <div>
          <p className="text-xs text-gray-500 mb-1">Required tools (present on host)</p>
          <ul className="flex flex-wrap gap-1">
            {result.required_tools.map(t => (
              <li key={t} className="px-2 py-0.5 bg-green-50 border border-green-200 rounded text-xs font-mono">{t}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex gap-4 text-xs text-gray-600">
        <span>Python backend: <strong>{result.python_backend ? 'yes' : 'no'}</strong></span>
        <span>Node frontend: <strong>{result.node_frontend ? 'yes' : 'no'}</strong></span>
      </div>
      {result.deploy_profile && (
        <div>
          <p className="text-xs text-gray-500 mb-1">Deploy profile — {result.deploy_profile.project} v{result.deploy_profile.version}</p>
          <ul className="space-y-1">
            {result.deploy_profile.components.map(c => (
              <li key={c.name} className="text-xs font-mono text-gray-700">
                <span className="font-semibold">{c.name}</span>
                {' '}
                <span className="text-gray-400">({c.type})</span>
                {' '}
                {c.service || c.command}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function DeployerPage({ projectId }) {
  const [status, setStatus] = useState(null)
  const [analysisStatus, setAnalysisStatus] = useState(null)
  const [scriptsStatus, setScriptsStatus] = useState(null)
  const [scanResult, setScanResult] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState(null)

  const isRunning = status?.state === 'running'
  const isAnalysing = analysisStatus?.state === 'running'
  const isGeneratingScripts = scriptsStatus?.state === 'running'
  const pollingDelay = !status || status.state === 'idle' || isRunning ? 5000 : null
  const analysisPollingDelay = isAnalysing ? 5000 : null
  const scriptsPollingDelay = isGeneratingScripts ? 5000 : null

  const refreshStatus = useCallback(() => {
    deployerApi.getDeployerStatus(projectId)
      .then(res => { setStatus(res.data); setError(null) })
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [projectId])

  const refreshAnalysisStatus = useCallback(() => {
    deployerApi.getAnalysisStatus(projectId)
      .then(res => setAnalysisStatus(res.data))
      .catch(() => {})
  }, [projectId])

  const refreshScriptsStatus = useCallback(() => {
    deployerApi.getScriptsStatus(projectId)
      .then(res => setScriptsStatus(res.data))
      .catch(() => {})
  }, [projectId])

  usePolling(refreshStatus, pollingDelay, projectId)
  usePolling(refreshAnalysisStatus, analysisPollingDelay, projectId)
  usePolling(refreshScriptsStatus, scriptsPollingDelay, projectId)

  useEffect(() => {
    refreshAnalysisStatus()
    refreshScriptsStatus()
  }, [projectId]) // eslint-disable-line

  const handleScan = async () => {
    setScanning(true)
    setError(null)
    try {
      const res = await deployerApi.scanProject(projectId)
      setScanResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setScanning(false)
    }
  }

  const handleAnalyze = async () => {
    setError(null)
    try {
      const res = await deployerApi.analyzeProject(projectId)
      setAnalysisStatus(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  const handleGenerateScripts = async () => {
    setError(null)
    try {
      const res = await deployerApi.generateScripts(projectId)
      setScriptsStatus(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-4">Deployer</h1>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <StatusBadge status={status} />
      <div className="flex gap-2 flex-wrap">
        <ActionButton
          label="Deploy"
          action={() => deployerApi.triggerDeploy(projectId)}
          disabled={isRunning}
          onSuccess={refreshStatus}
        />
        <ActionButton
          label="Restart"
          action={() => deployerApi.triggerRestart(projectId)}
          disabled={isRunning}
          onSuccess={refreshStatus}
        />
        <ActionButton
          label="Scan Project"
          action={handleScan}
          disabled={scanning}
        />
        <ActionButton
          label="Analyze Project"
          action={handleAnalyze}
          disabled={isAnalysing}
        />
        <ActionButton
          label="Generate Scripts"
          action={handleGenerateScripts}
          disabled={isGeneratingScripts}
        />
      </div>
      <LogsPanel projectId={projectId} isRunning={isRunning} />
      <AnalysisStatusPanel status={analysisStatus} />
      <AnalysisLogsPanel projectId={projectId} isRunning={isAnalysing} />
      <ScriptsStatusPanel status={scriptsStatus} />
      <ScriptsLogsPanel projectId={projectId} isRunning={isGeneratingScripts} />
      <ScanResultPanel result={scanResult} />
    </div>
  )
}
