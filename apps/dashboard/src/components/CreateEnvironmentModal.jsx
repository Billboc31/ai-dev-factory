import { useState } from 'react'
import * as api from '../api/environments'

const ENV_TYPES = ['main', 'develop', 'integration', 'preview', 'sandbox', 'feature', 'custom']
const REF_TYPES = ['branch', 'tag', 'commit', 'pr_ref']

export default function CreateEnvironmentModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    env_name: '',
    project_root: '',
    ref: '',
    ref_type: 'branch',
    env_type: 'feature',
    deployment_mode: 'deploy_and_test',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  function set(field) {
    return (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))
  }

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const payload = {
        env_name: form.env_name,
        project_root: form.project_root,
        ref: form.ref || null,
        ref_type: form.ref ? form.ref_type : null,
        env_type: form.env_type || null,
        deployment_mode: form.deployment_mode || null,
      }
      await api.createEnvironment(payload)
      onCreated()
      onClose()
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
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
              onChange={set('env_name')}
              placeholder="e.g. feature/my-branch"
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
