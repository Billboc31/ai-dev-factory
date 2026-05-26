import { useState } from 'react'
import usePolling from '../hooks/usePolling'
import * as api from '../api/environments'
import EnvironmentCard from '../components/EnvironmentCard'
import CreateEnvironmentModal from '../components/CreateEnvironmentModal'
import ErrorBanner from '../components/ErrorBanner'

export default function EnvironmentsPage() {
  const [environments, setEnvironments] = useState([])
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)

  async function load() {
    try {
      const res = await api.listEnvironments()
      setEnvironments(res.data)
      setError(null)
    } catch (e) {
      setError(e?.response?.data?.detail ?? e.message)
    }
  }

  usePolling(load, 5000)

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Environments</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
        >
          New Environment
        </button>
      </div>

      {error && <ErrorBanner message={error} onClose={() => setError(null)} />}

      {environments.length === 0 ? (
        <p className="text-gray-500 text-sm">No environments yet. Deploy one to get started.</p>
      ) : (
        <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
          {environments.map((env) => (
            <EnvironmentCard key={env.id} env={env} onAction={load} />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateEnvironmentModal
          onClose={() => setShowCreate(false)}
          onCreated={load}
        />
      )}
    </div>
  )
}
