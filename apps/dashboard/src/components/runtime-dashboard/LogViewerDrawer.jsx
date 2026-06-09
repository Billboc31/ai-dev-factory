import { useCallback, useEffect, useRef, useState } from 'react'
import usePolling from '../../hooks/usePolling'
import * as api from '../../api/runtimeDashboard'

function ProbeBadge({ result }) {
  const isPass = result === 'pass'
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold ${
      isPass ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
    }`}>
      {isPass ? 'PASS' : 'FAIL'}
    </span>
  )
}

function HealthcheckDiagnostics({ diagnostics, loaded }) {
  if (!loaded) {
    return (
      <div className="border-b border-gray-700 pb-4 mb-4">
        <p className="text-xs text-gray-400">Loading failure details…</p>
      </div>
    )
  }
  if (!diagnostics) return null
  const { probes = [], passed, failed, exit_code, raw_stderr } = diagnostics
  return (
    <div className="border-b border-gray-700 pb-4 mb-4">
      <h3 className="text-xs font-semibold text-yellow-400 uppercase mb-3">Failure details</h3>
      {probes.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-400 text-left">
                <th className="pb-1 pr-3 font-medium">Probe</th>
                <th className="pb-1 pr-3 font-medium">URL</th>
                <th className="pb-1 pr-3 font-medium">Result</th>
                <th className="pb-1 pr-3 font-medium">HTTP</th>
                <th className="pb-1 font-medium">Note</th>
              </tr>
            </thead>
            <tbody>
              {probes.map((probe, i) => (
                <tr key={i} className="border-t border-gray-800">
                  <td className="py-1 pr-3 font-mono text-gray-300">{probe.name}</td>
                  <td className="py-1 pr-3 font-mono text-gray-400 break-all">{probe.url}</td>
                  <td className="py-1 pr-3"><ProbeBadge result={probe.result} /></td>
                  <td className="py-1 pr-3 font-mono text-gray-300">{probe.http_code || '—'}</td>
                  <td className="py-1 text-gray-400">{probe.note || ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-xs text-gray-500">No probe data captured.</p>
      )}
      <div className="mt-2 flex gap-4 text-xs">
        <span className="text-green-400">{passed} passed</span>
        <span className="text-red-400">{failed} failed</span>
        <span className="text-gray-400">exit {exit_code}</span>
      </div>
      {raw_stderr && (
        <details className="mt-2">
          <summary className="text-xs text-gray-400 cursor-pointer select-none">stderr</summary>
          <pre className="text-xs text-orange-300 whitespace-pre-wrap mt-1">{raw_stderr}</pre>
        </details>
      )}
    </div>
  )
}

export default function LogViewerDrawer({ sandboxId, failingStep, onClose }) {
  const [content, setContent] = useState('')
  const [diagnostics, setDiagnostics] = useState(null)
  const [diagLoaded, setDiagLoaded] = useState(false)
  const offsetRef = useRef(0)
  const containerRef = useRef(null)
  const isHealthcheckFailure = failingStep === 'healthcheck.sh'

  useEffect(() => {
    setContent('')
    setDiagnostics(null)
    setDiagLoaded(false)
    offsetRef.current = 0
  }, [sandboxId])

  useEffect(() => {
    if (!sandboxId || !isHealthcheckFailure) return
    api.getSandboxDiagnostics(sandboxId)
      .then(res => {
        setDiagnostics(res.data.healthcheck_diagnostics)
        setDiagLoaded(true)
      })
      .catch(() => {
        setDiagLoaded(true)
      })
  }, [sandboxId, isHealthcheckFailure])

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [content])

  const fetchLogs = useCallback(async () => {
    if (!sandboxId) return
    try {
      const res = await api.getSandboxLogs(sandboxId, offsetRef.current)
      const { content: newChunk, next_offset: nextOffset } = res.data
      if (newChunk) {
        setContent(prev => prev + newChunk)
        offsetRef.current = nextOffset
      }
    } catch {
      // ignore transient fetch errors
    }
  }, [sandboxId])

  // key=sandboxId restarts polling when a different sandbox is opened
  usePolling(fetchLogs, 2000, sandboxId)

  function downloadLogs() {
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${sandboxId}.log`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="fixed inset-0 flex justify-end z-50">
      <div
        className="bg-black/40 flex-1"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="bg-gray-900 w-1/2 flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <span className="text-sm font-semibold text-gray-200">Logs — {sandboxId}</span>
          <div className="flex items-center gap-2">
            {content && (
              <>
                <button
                  onClick={() => navigator.clipboard?.writeText(content).catch(() => {})}
                  className="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300"
                >
                  Copy
                </button>
                <button
                  onClick={downloadLogs}
                  className="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300"
                >
                  Download
                </button>
              </>
            )}
            <button
              className="text-gray-400 hover:text-white text-lg leading-none"
              onClick={onClose}
            >
              ×
            </button>
          </div>
        </div>
        <div ref={containerRef} className="flex-1 overflow-y-auto p-4">
          {isHealthcheckFailure && (
            <HealthcheckDiagnostics diagnostics={diagnostics} loaded={diagLoaded} />
          )}
          {content ? (
            <pre className="text-xs text-green-300 whitespace-pre-wrap">{content}</pre>
          ) : (
            <p className="text-gray-500 text-xs">No logs available yet…</p>
          )}
        </div>
      </div>
    </div>
  )
}
