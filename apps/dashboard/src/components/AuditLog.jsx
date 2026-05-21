import { useEffect, useState } from 'react'
import * as api from '../api/tickets'

function StatusBadge({ ok }) {
  return ok
    ? <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">ok</span>
    : <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">error</span>
}

export default function AuditLog({ ticketId }) {
  const [events, setEvents] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setEvents(null)
    setError(null)
    api.getAuditLog(ticketId)
      .then(res => setEvents(res.data))
      .catch(err => setError(err.response?.data?.detail || err.message))
  }, [ticketId])

  if (error) return <p className="text-red-600 text-sm">{error}</p>
  if (events === null) return <p className="text-gray-500 text-sm">Loading…</p>
  if (events.length === 0) return <p className="text-gray-500 text-sm">No audit events yet.</p>

  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="border-b border-gray-200">
          <th className="text-left py-2 pr-4 text-gray-600 font-medium">Timestamp</th>
          <th className="text-left py-2 pr-4 text-gray-600 font-medium">Action</th>
          <th className="text-left py-2 pr-4 text-gray-600 font-medium">Status</th>
          <th className="text-left py-2 text-gray-600 font-medium">Message</th>
        </tr>
      </thead>
      <tbody>
        {events.map(e => (
          <tr key={e.id} className="border-b border-gray-100">
            <td className="py-2 pr-4 font-mono text-xs text-gray-500 whitespace-nowrap">{e.created_at}</td>
            <td className="py-2 pr-4 font-mono text-xs">{e.event_type.replace('action:', '')}</td>
            <td className="py-2 pr-4"><StatusBadge ok={e.metadata?.ok ?? true} /></td>
            <td className="py-2 text-xs text-gray-700 break-all">{e.message}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
