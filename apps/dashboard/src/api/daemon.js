import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

const _pfx = (projectId) => projectId ? `/projects/${projectId}` : ''

export const getDaemonStatus = (projectId) => client.get(`${_pfx(projectId)}/daemon/status`)
export const getDaemonActivity = (projectId, lines = 50) => client.get(`${_pfx(projectId)}/daemon/activity`, { params: { lines } })
export const startDaemon = (projectId) => client.post(`${_pfx(projectId)}/daemon/start`)
export const stopDaemon = (projectId) => client.post(`${_pfx(projectId)}/daemon/stop`)
export const restartDaemon = (projectId) => client.post(`${_pfx(projectId)}/daemon/restart`)
export const getBoardData = (projectId) => client.get(`${_pfx(projectId)}/daemon/board`)
export const syncMain = (projectId) => client.post(`${_pfx(projectId)}/daemon/sync-main`)
export const getRuntimeStatus = (projectId) => client.get(`${_pfx(projectId)}/daemon/runtime-status`)
