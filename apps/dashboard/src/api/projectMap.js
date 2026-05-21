import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

const _pfx = (projectId) => projectId ? `/projects/${projectId}` : ''

export const getProjectMap = (projectId) => client.get(`${_pfx(projectId)}/project-map`)
export const getProjectMapActivity = (projectId) => client.get(`${_pfx(projectId)}/project-map/activity`)
export const refreshProjectMap = (projectId) => client.post(`${_pfx(projectId)}/project-map/refresh`)
