import { useCallback, useState } from 'react'
import { getDaemonActivity } from '../api/daemon'
import usePolling from '../hooks/usePolling'

export default function DaemonActivityFeed({ lines = 50, projectId }) {
  const [activity, setActivity] = useState([])
  const [error, setError] = useState(null)

  const fetchActivity = useCallback(() => {
    getDaemonActivity(projectId, lines)
      .then(res => { setActivity(res.data.lines || []); setError(null) })
      .catch(() => setError('Unable to load activity feed'))
  }, [lines, projectId])

  usePolling(fetchActivity, 5000, projectId)

  if (error) return <p className="text-xs text-red-500">{error}</p>

  if (activity.length === 0) {
    return <p className="text-xs text-gray-400">Aucune activité</p>
  }

  return (
    <div className="bg-gray-900 text-green-400 rounded p-3 font-mono text-xs overflow-auto max-h-64">
      {activity.map((line, i) => (
        <div key={i}>{line}</div>
      ))}
    </div>
  )
}
