import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const listSandboxes = () => client.get('/sandboxes')
export const createSandbox = (ticketId, projectRoot) =>
  client.post('/sandboxes', { ticket_id: ticketId, project_root: projectRoot })
export const getSandbox = (id) => client.get(`/sandboxes/${id}`)
export const startSandbox = (id) => client.post(`/sandboxes/${id}/start`)
export const stopSandbox = (id) => client.post(`/sandboxes/${id}/stop`)
export const destroySandbox = (id) => client.delete(`/sandboxes/${id}`)
export const getSandboxLogs = (id, component) =>
  client.get(`/sandboxes/${id}/logs`, { params: component ? { component } : {} })
export const cleanupSandboxes = (maxAgeDays = 7) =>
  client.post('/sandboxes/cleanup', null, { params: { max_age_days: maxAgeDays } })
