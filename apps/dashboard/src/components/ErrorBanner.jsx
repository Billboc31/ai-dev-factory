export default function ErrorBanner({ message, onClose }) {
  if (!message) return null
  return (
    <div role="alert" className="bg-red-50 border border-red-300 text-red-700 px-4 py-3 rounded flex justify-between items-start mb-4">
      <span>{message}</span>
      {onClose && (
        <button
          onClick={onClose}
          aria-label="Dismiss error"
          className="ml-4 text-red-400 hover:text-red-600 text-lg leading-none"
        >
          ×
        </button>
      )}
    </div>
  )
}
