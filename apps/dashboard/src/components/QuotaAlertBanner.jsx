import { useCallback, useContext, useState } from 'react'
import { ActiveProjectContext } from '../App'
import { getRuntimeStatus } from '../api/daemon'
import usePolling from '../hooks/usePolling'

function formatWhen(iso) {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

export default function QuotaAlertBanner() {
  const projectId = useContext(ActiveProjectContext)
  const [alert, setAlert] = useState(null)

  const fetchStatus = useCallback(() => {
    if (!projectId) {
      setAlert(null)
      return
    }
    getRuntimeStatus(projectId)
      .then(res => setAlert(res.data?.provider_quota_alert ?? null))
      .catch(() => setAlert(null))
  }, [projectId])

  usePolling(fetchStatus, 10000, projectId)

  if (!alert?.active) {
    return null
  }

  const resumeAt = formatWhen(alert.reset_at || alert.cooldown_until)
  const tickets = alert.affected_tickets?.length
    ? alert.affected_tickets.join(', ')
    : null

  return (
    <div
      className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-950 shadow-sm"
      role="alert"
      aria-live="polite"
    >
      <p className="font-semibold text-sm">
        Quota {alert.provider === 'claude' ? 'Claude' : alert.provider} atteint
      </p>
      <p className="text-sm mt-1">
        {alert.message || 'Les agents sont en pause jusqu’au prochain reset du quota.'}
      </p>
      <p className="text-xs mt-2 text-amber-800">
        {resumeAt
          ? `Reprise automatique prévue vers ${resumeAt}. Le daemon relancera les tickets bloqués dès que le cooldown sera écoulé.`
          : 'Reprise automatique dès que le cooldown sera écoulé.'}
        {tickets && (
          <span className="block mt-1 font-mono">Tickets concernés : {tickets}</span>
        )}
      </p>
    </div>
  )
}
