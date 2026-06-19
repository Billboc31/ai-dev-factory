import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  startAgentLayout,
  getAgentLayoutLatest,
  getAgentLayoutJob,
  getAgentLayoutLogs,
  getAgentLayoutFiles,
  getAgentLayoutFile,
} from '../api/projects'
import ErrorBanner from '../components/ErrorBanner'
import usePolling from '../hooks/usePolling'

const STATUS_STYLES = {
  running: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
}

function StatusBadge({ status }) {
  if (!status) return null
  const cls = STATUS_STYLES[status] || 'bg-gray-100 text-gray-700'
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>
      {status === 'running' && (
        <span className="inline-block w-2 h-2 rounded-full bg-blue-500 mr-1 animate-pulse align-middle" />
      )}
      {status}
    </span>
  )
}

function FileBadge({ status }) {
  const map = { A: 'bg-green-100 text-green-700', M: 'bg-amber-100 text-amber-700', D: 'bg-red-100 text-red-700' }
  const label = { A: 'created', M: 'modified', D: 'deleted' }[status] || status
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${map[status] || 'bg-gray-100 text-gray-600'}`}>
      {label}
    </span>
  )
}

export default function ProjectAgentLayoutPage() {
  const { projectId } = useParams()
  const [job, setJob] = useState(null)
  const [logText, setLogText] = useState('')
  const [files, setFiles] = useState(null)
  const [selected, setSelected] = useState(null)
  const [fileDetail, setFileDetail] = useState(null)
  const [fileLoading, setFileLoading] = useState(false)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState(null)

  const logOffsetRef = useRef(0)
  const logEndRef = useRef(null)

  const jobId = job?.job_id || null
  const status = job?.status || null
  const running = status === 'running'
  const result = job?.result || {}
  const branch = result.branch || job?.branch
  const prUrl = result.pr_url
  const summary = result.analysis_summary
  const warnings = result.warnings || []
  const jobError = result.error || job?.error

  const fetchLogs = useCallback((id) => {
    if (!id) return
    getAgentLayoutLogs(projectId, id, logOffsetRef.current)
      .then(res => {
        const { text, offset } = res.data || {}
        if (text) setLogText(prev => prev + text)
        if (typeof offset === 'number') logOffsetRef.current = offset
      })
      .catch(() => {})
  }, [projectId])

  const fetchStatus = useCallback((id) => {
    if (!id) return
    getAgentLayoutJob(projectId, id)
      .then(res => setJob(res.data))
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [projectId])

  const fetchFiles = useCallback((id) => {
    if (!id) return
    getAgentLayoutFiles(projectId, id)
      .then(res => setFiles(res.data))
      .catch(() => {})
  }, [projectId])

  // Load the most recent job on mount / project change.
  useEffect(() => {
    setJob(null)
    setLogText('')
    setFiles(null)
    setSelected(null)
    setFileDetail(null)
    logOffsetRef.current = 0
    getAgentLayoutLatest(projectId)
      .then(res => setJob(res.data))
      .catch(() => {}) // 404 = no job yet
  }, [projectId])

  // When the active job id changes, reset the log stream and pull from the start.
  useEffect(() => {
    if (!jobId) return
    logOffsetRef.current = 0
    setLogText('')
    fetchLogs(jobId)
  }, [jobId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Poll status + logs while the job is running.
  usePolling(() => {
    fetchStatus(jobId)
    fetchLogs(jobId)
  }, running ? 2000 : null, jobId)

  // On terminal status, grab the log tail once and the file list.
  useEffect(() => {
    if (!jobId) return
    if (status === 'done' || status === 'error') {
      fetchLogs(jobId)
      fetchFiles(jobId)
    }
  }, [status, jobId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-scroll the log view while running.
  useEffect(() => {
    if (running && logEndRef.current) {
      logEndRef.current.scrollIntoView({ block: 'end' })
    }
  }, [logText, running])

  const handleStart = () => {
    setStarting(true)
    setError(null)
    setFiles(null)
    setSelected(null)
    setFileDetail(null)
    setLogText('')
    logOffsetRef.current = 0
    startAgentLayout(projectId)
      .then(res => {
        setJob({ job_id: res.data.job_id, project_id: projectId, status: 'running' })
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setStarting(false))
  }

  const selectFile = (path) => {
    setSelected(path)
    setFileDetail(null)
    setFileLoading(true)
    getAgentLayoutFile(projectId, jobId, path)
      .then(res => setFileDetail(res.data))
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setFileLoading(false))
  }

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold flex items-center gap-3">
          Agent Layout
          <StatusBadge status={status} />
        </h1>
        <button
          onClick={handleStart}
          disabled={running || starting}
          className={`px-4 py-2 text-sm rounded font-medium transition-colors ${
            running || starting
              ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {starting ? 'Starting…' : running ? 'Running…' : job ? 'Re-run' : 'Run'}
        </button>
      </div>

      <p className="text-sm text-gray-500 mb-4">
        Scans <code className="font-mono">{projectId}</code>, generates AI documentation,
        ensures the standard <code className="font-mono">ai/</code> layout, commits the
        changes and opens a pull request.
      </p>

      <ErrorBanner message={error} onClose={() => setError(null)} />

      {/* Summary */}
      {job && (
        <div className="bg-white border border-gray-200 rounded p-4 mb-6 space-y-1 text-sm">
          {branch && (
            <p className="text-gray-600">Branch: <code className="font-mono">{branch}</code></p>
          )}
          {prUrl && (
            <p>
              <span className="text-gray-600">PR: </span>
              <a href={prUrl} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline font-mono break-all">
                {prUrl}
              </a>
            </p>
          )}
          {summary && <p className="text-gray-700 italic">{summary}</p>}
          {jobError && <p className="text-red-700 font-mono text-xs">{jobError}</p>}
          {warnings.length > 0 && (
            <div>
              <p className="text-orange-700 font-semibold text-xs">Warnings:</p>
              <ul className="mt-1 space-y-0.5">
                {warnings.map((w, i) => (
                  <li key={i} className="text-xs text-orange-700">{w}</li>
                ))}
              </ul>
            </div>
          )}
          {!branch && !prUrl && !summary && !jobError && warnings.length === 0 && (
            <p className="text-gray-400">No summary yet.</p>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Logs */}
        <div>
          <h2 className="text-lg font-semibold mb-2">Logs</h2>
          <pre className="bg-gray-900 text-gray-100 text-xs font-mono rounded p-3 h-96 overflow-auto whitespace-pre-wrap break-words">
            {logText || (job ? 'Waiting for output…' : 'No job started yet.')}
            <span ref={logEndRef} />
          </pre>
        </div>

        {/* Files */}
        <div>
          <h2 className="text-lg font-semibold mb-2">Files</h2>
          <div className="bg-white border border-gray-200 rounded h-96 overflow-auto">
            {!files && <p className="text-gray-400 text-sm p-3">{running ? 'Running…' : 'No files yet.'}</p>}
            {files && files.files.length === 0 && (
              <p className="text-gray-400 text-sm p-3">No changed files on this branch.</p>
            )}
            {files && files.files.length > 0 && (
              <ul className="divide-y divide-gray-100">
                {files.files.map(f => (
                  <li key={f.path}>
                    <button
                      onClick={() => selectFile(f.path)}
                      className={`w-full text-left px-3 py-2 text-xs font-mono flex items-center gap-2 hover:bg-gray-50 ${
                        selected === f.path ? 'bg-blue-50' : ''
                      }`}
                    >
                      <FileBadge status={f.status} />
                      <span className="truncate">{f.path}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {/* File detail */}
      {selected && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold mb-2 font-mono break-all">{selected}</h2>
          {fileLoading && <p className="text-gray-400 text-sm">Loading…</p>}
          {fileDetail && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-1">Content</p>
                <pre className="bg-gray-50 border border-gray-200 text-xs font-mono rounded p-3 max-h-96 overflow-auto whitespace-pre-wrap break-words">
                  {fileDetail.content || '(empty)'}
                </pre>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-1">Diff</p>
                <pre className="bg-gray-50 border border-gray-200 text-xs font-mono rounded p-3 max-h-96 overflow-auto whitespace-pre-wrap break-words">
                  {fileDetail.diff
                    ? fileDetail.diff.split('\n').map((line, i) => (
                        <div
                          key={i}
                          className={
                            line.startsWith('+') && !line.startsWith('+++')
                              ? 'text-green-700'
                              : line.startsWith('-') && !line.startsWith('---')
                              ? 'text-red-700'
                              : line.startsWith('@@')
                              ? 'text-blue-600'
                              : ''
                          }
                        >
                          {line || ' '}
                        </div>
                      ))
                    : '(no diff)'}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
