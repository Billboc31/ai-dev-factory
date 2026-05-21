import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

const _pfx = (projectId) => projectId ? `/projects/${projectId}` : ''

export const getDeployerStatus = (projectId) => client.get(`${_pfx(projectId)}/deployer/status`)
export const scanProject = (projectId) => client.post(`${_pfx(projectId)}/deployer/scan`)
