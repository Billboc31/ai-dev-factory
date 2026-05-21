import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

const _pfx = (projectId) => projectId ? `/projects/${projectId}` : ''

export const getDeployerStatus = (projectId) => client.get(`${_pfx(projectId)}/deployer/status`)
export const scanProject = (projectId) => client.post(`${_pfx(projectId)}/deployer/scan`)
export const triggerDeploy = (projectId) => client.post(`${_pfx(projectId)}/deployer/deploy`)
export const triggerRestart = (projectId) => client.post(`${_pfx(projectId)}/deployer/restart`)
export const getDeployLogs = (projectId, lines = 100) => client.get(`${_pfx(projectId)}/deployer/logs`, { params: { lines } })
