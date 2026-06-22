import { useCallback, useEffect, useState } from 'react'
import * as api from '../api/tickets'

const THRESHOLD_RULES = {
  max_estimated_cost_usd: { configKey: 'max_cost_usd', label: 'Max estimated cost (USD)', step: '0.01', min: 0 },
  max_difficulty: { configKey: 'max_difficulty', label: 'Max difficulty score', step: '1', min: 0 },
}

function isThresholdRule(ruleKey) {
  return Object.prototype.hasOwnProperty.call(THRESHOLD_RULES, ruleKey)
}

export default function ProjectRulesPanel({ projectId }) {
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState(null)
  const [info, setInfo] = useState(null)

  const fetchRules = useCallback(() => {
    setLoading(true)
    api.getProjectRules(projectId)
      .then(res => {
        setRules(res.data.rules || [])
        setErr(null)
      })
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    setInfo(null)
    fetchRules()
  }, [projectId, fetchRules])

  const toggleEnabled = (ruleKey) => {
    setRules(prev => prev.map(r => r.rule_key === ruleKey ? { ...r, enabled: !r.enabled } : r))
  }

  const updateThreshold = (ruleKey, value) => {
    const meta = THRESHOLD_RULES[ruleKey]
    if (!meta) return
    setRules(prev => prev.map(r => {
      if (r.rule_key !== ruleKey) return r
      const cfg = { ...(r.configuration || {}) }
      cfg[meta.configKey] = value === '' ? '' : Number(value)
      return { ...r, configuration: cfg }
    }))
  }

  const handleSave = () => {
    setSaving(true)
    setErr(null)
    setInfo(null)
    const payload = {
      rules: rules.map(r => ({
        rule_key: r.rule_key,
        enabled: !!r.enabled,
        configuration: r.configuration || {},
      })),
    }
    api.putProjectRules(projectId, payload)
      .then(res => {
        setRules(res.data.rules || [])
        setInfo('Rules saved.')
      })
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setSaving(false))
  }

  const handleResetDefaults = () => {
    setSaving(true)
    setErr(null)
    setInfo(null)
    api.putProjectRules(projectId, { action: 'reset_defaults' })
      .then(res => {
        setRules(res.data.rules || [])
        setInfo('Reset to defaults.')
      })
      .catch(e => setErr(e.response?.data?.detail || e.message))
      .finally(() => setSaving(false))
  }

  return (
    <div className="bg-white border border-gray-200 rounded p-4 space-y-4 mb-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-700">Project Rules</h2>
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
            Advisory only — does not gate execution
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleResetDefaults}
            disabled={saving || loading}
            className="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
          >
            Reset to defaults
          </button>
          <button
            onClick={handleSave}
            disabled={saving || loading}
            className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>

      {err && <p className="text-red-600 text-xs">{err}</p>}
      {info && <p className="text-emerald-700 text-xs">{info}</p>}

      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <ul className="space-y-3">
          {rules.map(rule => {
            const threshold = THRESHOLD_RULES[rule.rule_key]
            return (
              <li key={rule.rule_key} className="border border-gray-100 rounded p-3 flex flex-col gap-2">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-gray-800 font-mono">{rule.rule_key}</p>
                    {rule.description && (
                      <p className="text-xs text-gray-500 mt-0.5">{rule.description}</p>
                    )}
                  </div>
                  <label className="inline-flex items-center gap-2 text-xs text-gray-600">
                    <input
                      type="checkbox"
                      checked={!!rule.enabled}
                      onChange={() => toggleEnabled(rule.rule_key)}
                      aria-label={`Toggle ${rule.rule_key}`}
                    />
                    Enabled
                  </label>
                </div>
                {threshold && (
                  <div className="flex items-center gap-2">
                    <label className="text-xs text-gray-600" htmlFor={`cfg-${rule.rule_key}`}>
                      {threshold.label}
                    </label>
                    <input
                      id={`cfg-${rule.rule_key}`}
                      type="number"
                      step={threshold.step}
                      min={threshold.min}
                      value={
                        rule.configuration && rule.configuration[threshold.configKey] !== undefined
                          ? rule.configuration[threshold.configKey]
                          : ''
                      }
                      onChange={(e) => updateThreshold(rule.rule_key, e.target.value)}
                      className="w-28 px-2 py-1 text-xs border border-gray-300 rounded"
                    />
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
