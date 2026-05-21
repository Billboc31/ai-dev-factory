import { useState } from 'react'

const VARIANT_CLASSES = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
  danger: 'bg-red-600 text-white hover:bg-red-700'
}

export default function ActionButton({ label, action, variant = 'primary', onSuccess, onResult, disabled: externalDisabled }) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleClick = async () => {
    setLoading(true)
    setResult(null)
    try {
      const res = await action()
      const data = res?.data || {}
      const message = data.message || 'Done'
      const ok = data.ok !== false
      setResult({ ok, message })
      onResult?.(data)
      if (ok) onSuccess?.()
    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Unknown error'
      setResult({ ok: false, message })
      onResult?.(err.response?.data || null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="inline-flex flex-col items-start gap-1">
      <button
        onClick={handleClick}
        disabled={loading || !!externalDisabled}
        className={`px-3 py-1.5 rounded text-sm font-medium disabled:opacity-50 ${VARIANT_CLASSES[variant] || VARIANT_CLASSES.primary}`}
      >
        {loading ? '…' : label}
      </button>
      {result && (
        <span className={`text-xs ${result.ok ? 'text-green-600' : 'text-red-600'}`}>
          {result.message}
        </span>
      )}
    </div>
  )
}
