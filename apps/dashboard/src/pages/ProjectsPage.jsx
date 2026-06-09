import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import usePolling from '../hooks/usePolling'
import { listProjects } from '../api/projects'
import ErrorBanner from '../components/ErrorBanner'

export default function ProjectsPage() {
  const [projects, setProjects] = useState([])
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  async function load() {
    try {
      const res = await listProjects()
      setProjects(res.data)
      setError(null)
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message)
    }
  }

  usePolling(load, 5000)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Projects</h1>
        <button
          onClick={() => navigate('/import-project')}
          className="px-4 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
        >
          Import project
        </button>
      </div>

      {error && <ErrorBanner message={error} onClose={() => setError(null)} />}

      {projects.length === 0 ? (
        <p className="text-gray-500 text-sm">No projects registered. Import one to get started.</p>
      ) : (
        <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
          {projects.map((p) => (
            <div key={p.name} className="border rounded-lg p-4 bg-white shadow-sm flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-gray-900">{p.name}</span>
                {p.stack && (
                  <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">{p.stack}</span>
                )}
              </div>
              <span className="text-xs text-gray-500 truncate">{p.root}</span>
              {p.runtime_root && (
                <span className="text-xs text-gray-400 truncate">runtime: {p.runtime_root}</span>
              )}
              <span className="text-xs text-gray-500">{p.tickets_count} ticket(s)</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
