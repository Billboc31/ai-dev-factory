export default function RuntimeHealthPanel({ health }) {
  if (!health) {
    return <p className="text-sm text-gray-400">Loading health data…</p>
  }

  const supervisorColor =
    health.supervisor_status === 'up'
      ? 'text-green-600'
      : health.supervisor_status === 'down'
      ? 'text-red-600'
      : 'text-gray-500'

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-white border border-gray-200 rounded p-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Supervisor</h3>
        <p className={`text-sm font-medium ${supervisorColor}`}>{health.supervisor_status}</p>
      </div>

      <div className="bg-white border border-gray-200 rounded p-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Active Jobs</h3>
        <p className="text-2xl font-bold text-gray-800">{health.active_jobs}</p>
      </div>

      <div className="bg-white border border-gray-200 rounded p-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Stale PID Files</h3>
        {health.stale_pid_files.length === 0 ? (
          <p className="text-xs text-gray-400">None</p>
        ) : (
          <ul className="text-xs text-red-600 space-y-0.5">
            {health.stale_pid_files.map(f => (
              <li key={f} className="font-mono">{f}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="bg-white border border-gray-200 rounded p-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">Stale Locks</h3>
        {health.stale_locks.length === 0 ? (
          <p className="text-xs text-gray-400">None</p>
        ) : (
          <ul className="text-xs text-orange-600 space-y-0.5">
            {health.stale_locks.map(f => (
              <li key={f} className="font-mono">{f}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
