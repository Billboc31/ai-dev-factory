import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

const _pfx = (projectId) => projectId ? `/projects/${projectId}` : ''

export const getDeployerStatus = (projectId) => client.get(`${_pfx(projectId)}/deployer/status`)
export const scanProject = (projectId) => client.post(`${_pfx(projectId)}/deployer/scan`)
export const triggerDeploy = (projectId) => client.post(`${_pfx(projectId)}/deployer/deploy`)
export const triggerRestart = (projectId) => client.post(`${_pfx(projectId)}/deployer/restart`)
export const getDeployLogs = (projectId, lines = 100) => client.get(`${_pfx(projectId)}/deployer/logs`, { params: { lines } })
export const analyzeProject = (projectId) => client.post(`${_pfx(projectId)}/deployer/analyze`)
export const getAnalysisStatus = (projectId) => client.get(`${_pfx(projectId)}/deployer/analysis/status`)
export const getAnalysisLogs = (projectId, lines = 100) => client.get(`${_pfx(projectId)}/deployer/analysis/logs`, { params: { lines } })
// T132 — AI-generated operational scripts (`deployer/scripts/*`).
export const generateScripts = (projectId) => client.post(`${_pfx(projectId)}/deployer/generate-scripts`)
export const getScriptsStatus = (projectId) => client.get(`${_pfx(projectId)}/deployer/scripts/status`)
export const getScriptsLogs = (projectId, lines = 100) => client.get(`${_pfx(projectId)}/deployer/scripts/logs`, { params: { lines } })
// T134 — per-project deploy-validation pipeline (`sandbox/*`).
export const startSandboxValidation = (projectId) => client.post(`${_pfx(projectId)}/sandbox/start`, null, { params: { mode: 'validation' } })
export const startSandboxEnvironment = (projectId) => client.post(`${_pfx(projectId)}/sandbox/start`, null, { params: { mode: 'environment' } })
export const getSandboxStatus = (projectId) => client.get(`${_pfx(projectId)}/sandbox/status`)
export const getSandboxLogs = (projectId, lines = 100) => client.get(`${_pfx(projectId)}/sandbox/logs`, { params: { lines } })
export const stopSandboxEnvironment = (projectId) => client.post(`${_pfx(projectId)}/sandbox/stop`)
export const deleteSandboxEnvironment = (projectId) => client.delete(`${_pfx(projectId)}/sandbox`)
// T137 — historical sandbox-runs listing and cleanup (`/sandbox-runs`).
export const listSandboxRuns = () => client.get('/sandbox-runs')
export const getSandboxRunLogs = (sandboxId, lines = 500) => client.get(`/sandbox-runs/${sandboxId}/logs`, { params: { lines } })
export const cleanupSandboxRun = (sandboxId) => client.delete(`/sandbox-runs/${sandboxId}`)
