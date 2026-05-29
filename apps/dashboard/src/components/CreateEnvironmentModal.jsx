import { useState } from 'react'
import * as api from '../api/environments'

const ENV_TYPES = ['main', 'develop', 'integration', 'preview', 'sandbox', 'feature', 'custom']
const REF_TYPES = ['branch', 'tag', 'commit', 'pr_ref']
const HOST_SUFFIX = 'ai-dev-factory.localhost'

function slugify(name) {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 50)
}

export default function CreateEnvironmentModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    env_name: '',
    project_root: '',
    ref: '',
    ref_type: 'branch',
    env_type: 'feature',
    deployment_mode: 'deploy_and_test',
    web_host: '',
    api_host: '',
  })
  const [hostManual, setHostManual] = useState({ web_host: false, api_host: false })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})

  function set(field) {
    return (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))
  }

  function handleEnvNameChange(e) {
    const name = e.target.value
    const slug = slugify(name)
    setForm((prev) => ({
      ...prev,
      env_name: name,
      web_host: hostManual.web_host ? prev.web_host : (slug ? `${slug}.${HOST_SUFFIX}` : ''),
      api_host: hostManual.api_host ? prev.api_host : (slug ? `api.${slug}.${HOST_SUFFIX}` : ''),
    }))
  }

  function handleHostChange(field) {
    return (e) => {
      setHostManual((prev) => ({ ...prev, [field]: true }))
      setFieldErrors((prev) => ({ ...prev, [field]: undefined }))
      setForm((prev) => ({ ...prev, [field]: e.target.value }))
    }
  }

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setFieldErrors({})
    setBusy(true)
    try {
      const payload = {
        env_name: form.env_name,
        project_root: form.project_root,
        ref: form.ref || null,
        ref_type: form.ref ? form.ref_type : null,
        env_type: form.env_type || null,
        deployment_mode: form.deployment_mode || null,
        web_host: form.web_host || null,
        api_host: form.api_host || null,
      }
      await api.createEnvironment(payload)
      onCreated()
      onClose()
    } catch (err) {
      const detail = err?.response?.data?.detail ?? err.message
      if (typeof detail === 'string') {
        if (detail.startsWith('web_host:')) {
          setFieldErrors((prev) => ({ ...prev, web_host: detail.slice(9).trim() }))
        } else if (detail.startsWith('api_host:')) {
          setFieldErrors((prev) => ({ ...prev, api_host: detail.slice(9).trim() }))
        } else {
          setError(detail)
        }
      } else {
        setError(String(detail))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">New Environment</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl leading-none">×</button>
        </div>

        <form onSubmit={submit} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Environment Name *</span>
            <input
              required
              value={form.env_name}
              onChange={handleEnvNameChange}
              placeholder="e.g. Demo Client"
              className="border rounded px-2 py-1.5 text-sm"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Project Root *</span>
            <input
              required
              value={form.project_root}
              onChange={set('project_root')}
              placeholder="/path/to/project"
              className="border rounded px-2 py-1.5 text-sm font-mono"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Ref (branch / tag / commit / PR ref)</span>
            <input
              value={form.ref}
              onChange={set('ref')}
              placeholder="e.g. feature/my-branch or abc1234"
              className="border rounded px-2 py-1.5 text-sm font-mono"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Ref Type</span>
            <select value={form.ref_type} onChange={set('ref_type')} className="border rounded px-2 py-1.5 text-sm">
              {REF_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Environment Type</span>
            <select value={form.env_type} onChange={set('env_type')} className="border rounded px-2 py-1.5 text-sm">
              {ENV_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </label>

          <fieldset className="flex flex-col gap-1 text-sm">
            <legend className="font-medium">Deployment Mode</legend>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                value="deploy_and_test"
                checked={form.deployment_mode === 'deploy_and_test'}
                onChange={set('deployment_mode')}
              />
              Deploy & Test
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                value="persistent"
                checked={form.deployment_mode === 'persistent'}
                onChange={set('deployment_mode')}
              />
              Persistent Environment
            </label>
          </fieldset>

          <div className="border-t pt-3">
            <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">Traefik URLs</p>

            <div className="flex flex-col gap-2">
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Web Host</span>
                <input
                  value={form.web_host}
                  onChange={handleHostChange('web_host')}
                  placeholder={`demo-client.${HOST_SUFFIX}`}
                  className={`border rounded px-2 py-1.5 text-sm font-mono ${fieldErrors.web_host ? 'border-red-400' : ''}`}
                />
                {fieldErrors.web_host && (
                  <span className="text-xs text-red-600">{fieldErrors.web_host}</span>
                )}
              </label>

              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">API Host</span>
                <input
                  value={form.api_host}
                  onChange={handleHostChange('api_host')}
                  placeholder={`api.demo-client.${HOST_SUFFIX}`}
                  className={`border rounded px-2 py-1.5 text-sm font-mono ${fieldErrors.api_host ? 'border-red-400' : ''}`}
                />
                {fieldErrors.api_host && (
                  <span className="text-xs text-red-600">{fieldErrors.api_host}</span>
                )}
              </label>
            </div>

            {(form.web_host || form.api_host) && (
              <div className="mt-2 bg-gray-50 rounded p-2 text-xs">
                <p className="font-medium text-gray-600 mb-1">Preview</p>
                {form.web_host && (
                  <div>Web: <span className="font-mono text-blue-600">http://{form.web_host}</span></div>
                )}
                {form.api_host && (
                  <div>API: <span className="font-mono text-blue-600">http://{form.api_host}</span></div>
                )}
              </div>
            )}
          </div>

          {error && <p className="text-xs text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 mt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded border">
              Cancel
            </button>
            <button
              type="submit"
              disabled={busy}
              className="px-4 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {busy ? 'Deploying…' : 'Deploy'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
