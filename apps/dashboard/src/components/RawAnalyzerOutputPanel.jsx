import { useState } from 'react'

export default function RawAnalyzerOutputPanel({ raw }) {
  const [copied, setCopied] = useState(false)

  if (raw == null) {
    return (
      <details
        className="bg-white rounded border border-gray-200 p-3"
        data-testid="raw-analyzer-output"
      >
        <summary className="cursor-pointer text-sm font-semibold text-gray-700">
          Raw Dependency Analyzer Output
        </summary>
        <p className="mt-3 text-sm text-gray-400">
          Raw output not persisted for this batch.
        </p>
      </details>
    )
  }

  const jsonText = JSON.stringify(raw, null, 2)
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonText)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard API might be blocked in some environments; silent fallback.
    }
  }

  return (
    <details
      className="bg-white rounded border border-gray-200 p-3"
      data-testid="raw-analyzer-output"
    >
      <summary className="cursor-pointer text-sm font-semibold text-gray-700">
        Raw Dependency Analyzer Output
      </summary>
      <div className="mt-3">
        <button
          type="button"
          onClick={handleCopy}
          className="mb-2 px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded border border-gray-300"
        >
          {copied ? 'Copied' : 'Copy JSON'}
        </button>
        <pre className="text-xs bg-gray-50 border border-gray-200 rounded p-2 max-h-96 overflow-auto">
          {jsonText}
        </pre>
      </div>
    </details>
  )
}
