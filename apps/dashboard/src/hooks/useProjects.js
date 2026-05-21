import { useState, useCallback } from 'react'
import usePolling from './usePolling'

export default function useProjects() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchProjects = useCallback(async () => {
    try {
      const res = await fetch('/api/projects')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setProjects(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  usePolling(fetchProjects, 10000)

  return { projects, loading, error }
}
