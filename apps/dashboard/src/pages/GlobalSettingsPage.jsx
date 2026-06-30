import { useCallback, useEffect, useState, useContext } from 'react'
import { Link } from 'react-router-dom'
import { listSettings, updateSetting, resetSetting } from '../api/settings'
import ErrorBanner from '../components/ErrorBanner'
import { ActiveProjectContext } from '../App'

const SOURCE_BADGE = {
  db: 'bg-emerald-100 text-emerald-800',
  env: 'bg-sky-100 text-sky-800',
  default: 'bg-gray-200 text-gray-700',
}

function sourceBadgeClass(source) {
  return SOURCE_BADGE[source] || 'bg-gray-200 text-gray-700'
}

function valueDisplay(setting) {
  if (setting.is_sensitive) {
    return setting.value === 'configured' ? 'configured' : 'not configured'
  }
  if (setting.value_type === 'bool') {
    return setting.value === true || setting.value === 'true' ? 'true' : 'false'
  }
  if (setting.value === null || setting.value === undefined || setting.value === '') {
    return '—'
  }
  return String(setting.value)
}

function SettingEditor({ setting, onSave, onCancel, busy }) {
  const initial =
    setting.value_type === 'bool'
      ? Boolean(setting.value)
      : setting.value === null || setting.value === undefined
        ? ''
        : String(setting.value)
  const [draft, setDraft] = useState(initial)

  if (setting.value_type === 'bool') {
    return (
      <div className="flex items-center gap-2">
        <label className="inline-flex items-center gap-1 text-xs">
          <input
            type="checkbox"
            checked={Boolean(draft)}
            onChange={e => setDraft(e.target.checked)}
            disabled={busy}
          />
          <span>{Boolean(draft) ? 'true' : 'false'}</span>
        </label>
        <button
          className="px-2 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          onClick={() => onSave(Boolean(draft))}
          disabled={busy}
        >
          Save
        </button>
        <button
          className="px-2 py-1 text-xs rounded border border-gray-300 hover:bg-gray-100"
          onClick={onCancel}
          disabled={busy}
        >
          Cancel
        </button>
      </div>
    )
  }

  const inputType = setting.value_type === 'int' || setting.value_type === 'float' ? 'number' : 'text'
  return (
    <div className="flex items-center gap-2">
      <input
        className="px-2 py-1 text-xs border border-gray-300 rounded font-mono w-48"
        type={inputType}
        value={draft}
        onChange={e => setDraft(e.target.value)}
        disabled={busy}
      />
      <button
        className="px-2 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        onClick={() => onSave(draft)}
        disabled={busy}
      >
        Save
      </button>
      <button
        className="px-2 py-1 text-xs rounded border border-gray-300 hover:bg-gray-100"
        onClick={onCancel}
        disabled={busy}
      >
        Cancel
      </button>
    </div>
  )
}

export default function GlobalSettingsPage() {
  const activeProject = useContext(ActiveProjectContext)
  const [settings, setSettings] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editingKey, setEditingKey] = useState(null)
  const [busyKey, setBusyKey] = useState(null)
  const [restartHints, setRestartHints] = useState({})

  const refresh = useCallback(() => {
    setLoading(true)
    listSettings()
      .then(res => {
        setSettings(res.data?.settings || [])
        setError(null)
      })
      .catch(err => setError(err.response?.data?.detail || err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const handleSave = async (setting, value) => {
    setBusyKey(setting.key)
    try {
      await updateSetting(setting.key, value)
      if (setting.requires_restart) {
        setRestartHints(prev => ({ ...prev, [setting.key]: true }))
      }
      setEditingKey(null)
      refresh()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setBusyKey(null)
    }
  }

  const handleReset = async (setting) => {
    setBusyKey(setting.key)
    try {
      await resetSetting(setting.key)
      if (setting.requires_restart) {
        setRestartHints(prev => ({ ...prev, [setting.key]: true }))
      }
      refresh()
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setBusyKey(null)
    }
  }

  if (loading) return <p className="text-gray-500">Loading settings…</p>

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-bold mb-2">Global Settings</h1>
      <p className="text-sm text-gray-500 mb-4">
        Runtime values stored in the database. Precedence: DB override → .env → hardcoded default.
        Sensitive settings are read-only in V1 and only display configured / not configured.
      </p>

      {activeProject && (
        <p className="text-sm text-gray-600 mb-4">
          Per-project execution gates (Human Approval, cost limits, …) live in{' '}
          <Link
            to={`/projects/${activeProject}/rules`}
            className="text-blue-600 hover:text-blue-800 underline font-medium"
          >
            Execution Rules
          </Link>
          {' '}for project <span className="font-mono">{activeProject}</span>.
        </p>
      )}

      <ErrorBanner message={error} onClose={() => setError(null)} />

      <div className="bg-white rounded shadow border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-100 text-left text-gray-600">
              <th className="p-3 font-medium">Name</th>
              <th className="p-3 font-medium">Current value</th>
              <th className="p-3 font-medium">Description</th>
              <th className="p-3 font-medium">Editable</th>
              <th className="p-3 font-medium">Sensitive</th>
              <th className="p-3 font-medium">Requires restart</th>
              <th className="p-3 font-medium">Source</th>
              <th className="p-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {settings.map(setting => {
              const editing = editingKey === setting.key
              const busy = busyKey === setting.key
              const showRestartBadge = setting.requires_restart && restartHints[setting.key]
              return (
                <tr key={setting.key} className="border-t border-gray-100 align-top">
                  <td className="p-3 font-mono text-xs">{setting.key}</td>
                  <td className="p-3">
                    {editing ? (
                      <SettingEditor
                        setting={setting}
                        busy={busy}
                        onCancel={() => setEditingKey(null)}
                        onSave={value => handleSave(setting, value)}
                      />
                    ) : (
                      <span className="font-mono text-xs break-all">{valueDisplay(setting)}</span>
                    )}
                  </td>
                  <td className="p-3 text-xs text-gray-600">{setting.description || '—'}</td>
                  <td className="p-3 text-xs">
                    {setting.editable ? 'yes' : 'no'}
                  </td>
                  <td className="p-3 text-xs">{setting.is_sensitive ? 'yes' : 'no'}</td>
                  <td className="p-3 text-xs">
                    {setting.requires_restart ? (
                      <span className="inline-flex items-center gap-1">
                        <span>yes</span>
                        {showRestartBadge && (
                          <span className="px-2 py-0.5 rounded text-xs bg-amber-100 text-amber-800">
                            Restart required
                          </span>
                        )}
                      </span>
                    ) : (
                      'no'
                    )}
                  </td>
                  <td className="p-3 text-xs">
                    <span
                      className={`px-2 py-0.5 rounded text-xs uppercase tracking-wider ${sourceBadgeClass(setting.source)}`}
                    >
                      {setting.source}
                    </span>
                  </td>
                  <td className="p-3 text-xs">
                    {setting.is_sensitive ? (
                      <span className="text-gray-400" title="Secret editing will be supported by a future encrypted secret-management ticket.">
                        read-only in V1
                      </span>
                    ) : editing ? null : (
                      <div className="flex flex-col gap-1">
                        <button
                          className="px-2 py-1 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                          onClick={() => setEditingKey(setting.key)}
                          disabled={busy}
                        >
                          Edit
                        </button>
                        {setting.source === 'db' && (
                          <button
                            className="px-2 py-1 text-xs rounded border border-gray-300 hover:bg-gray-100 disabled:opacity-50"
                            onClick={() => handleReset(setting)}
                            disabled={busy}
                          >
                            Reset to default
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
            {settings.length === 0 && (
              <tr>
                <td colSpan={8} className="p-6 text-center text-gray-400">
                  No settings declared.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
