import { useEffect, useState } from 'react'
import { getDeployHistory } from '../api/workspace'

export default function DeployHistoryPanel({ projectId }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!projectId) return
    setLoading(true)
    getDeployHistory(projectId)
      .then(res => setHistory(res.data?.history ?? []))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) return <p className="text-xs text-gray-400 px-3 py-2">Loading history…</p>
  if (!history.length) return null

  return (
    <div className="border-t border-gray-200 px-3 py-2 shrink-0">
      <p className="text-xs font-semibold text-gray-600 mb-1">Deployment history</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-100">
              <th className="pr-2 py-0.5 font-medium">When</th>
              <th className="pr-2 py-0.5 font-medium">Status</th>
              <th className="pr-2 py-0.5 font-medium">SHA</th>
              <th className="py-0.5 font-medium">URL</th>
            </tr>
          </thead>
          <tbody>
            {history.map(row => (
              <tr key={row.deployment_id} className="border-b border-gray-50">
                <td className="pr-2 py-0.5 text-gray-500 whitespace-nowrap">
                  {row.started_at ? new Date(row.started_at).toLocaleString() : '—'}
                </td>
                <td className="pr-2 py-0.5">
                  <span className={`inline-block px-1.5 rounded font-mono ${
                    row.status === 'succeeded'
                      ? 'bg-green-100 text-green-700'
                      : row.status === 'failed'
                      ? 'bg-red-100 text-red-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {row.status}
                  </span>
                </td>
                <td className="pr-2 py-0.5 font-mono text-gray-500">
                  {row.deployed_sha ? row.deployed_sha.slice(0, 8) : '—'}
                </td>
                <td className="py-0.5">
                  {row.preview_url ? (
                    <a
                      href={row.preview_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 underline truncate max-w-[8rem] inline-block"
                    >
                      {row.preview_url}
                    </a>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
