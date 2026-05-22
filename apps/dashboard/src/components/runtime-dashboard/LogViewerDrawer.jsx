import { useCallback, useEffect, useRef, useState } from 'react'
import usePolling from '../../hooks/usePolling'
import * as api from '../../api/runtimeDashboard'

export default function LogViewerDrawer({ sandboxId, onClose }) {
  const [content, setContent] = useState('')
  const offsetRef = useRef(0)
  const containerRef = useRef(null)

  useEffect(() => {
    setContent('')
    offsetRef.current = 0
  }, [sandboxId])

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
          <button
            className="text-gray-400 hover:text-white text-lg leading-none"
            onClick={onClose}
          >
            ×
          </button>
        </div>
        <div ref={containerRef} className="flex-1 overflow-y-auto p-4">
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
