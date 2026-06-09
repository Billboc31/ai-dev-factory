import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { importProject } from '../api/projects'
import ErrorBanner from '../components/ErrorBanner'

function normalizeProjectId(raw) {
  return raw
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64)
}

export default function ImportProjectPage() {
  const [projectRoot, setProjectRoot] = useState('')
  const [projectId, setProjectId] = useState('')
  const [idEdited, setIdEdited] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  function handleRootChange(value) {
    setProjectRoot(value)
    if (!idEdited) {
      const basename = value.replace(/\\/g, '/').split('/').filter(Boolean).pop() ?? ''
      setProjectId(normalizeProjectId(basename))
    }
  }

  function handleIdChange(value) {
    setIdEdited(true)
    setProjectId(value)
  }

  const preview = normalizeProjectId(projectId)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await importProject(projectRoot.trim(), projectId.trim())
      navigate('/projects')
    } catch (e) {
      const msg = e?.response?.data?.detail ?? e.message
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-lg flex flex-col gap-4">
      <h1 className="text-xl font-bold">Import existing project</h1>

      {error && <ErrorBanner message={error} onClose={() => setError(null)} />}

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Local path</label>
          <input
            type="text"
            value={projectRoot}
            onChange={(e) => handleRootChange(e.target.value)}
            placeholder="/home/user/my-project"
            required
            className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <span className="text-xs text-gray-500">Absolute path to the existing git repository.</span>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Project ID</label>
          <input
            type="text"
            value={projectId}
            onChange={(e) => handleIdChange(e.target.value)}
            placeholder="my-project"
            required
            className="border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          {projectId !== preview && (
            <span className="text-xs text-yellow-600">
              Normalized preview: <strong>{preview || '—'}</strong>
            </span>
          )}
          <span className="text-xs text-gray-500">
            Lowercase letters, digits, hyphens and underscores only (max 64 chars).
          </span>
        </div>

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Importing…' : 'Import project'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/projects')}
            className="px-4 py-2 text-sm rounded border text-gray-600 hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
