import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const listSandboxRuns = () => client.get('/runtime-dashboard/sandbox-runs')
export const getSandboxLogs = (id, offset = 0) =>
  client.get(`/runtime-dashboard/sandbox-runs/${id}/logs`, { params: { offset } })
export const deleteSandboxRun = (id) => client.delete(`/runtime-dashboard/sandbox-runs/${id}`)

export const listProposalRuns = () => client.get('/runtime-dashboard/proposal-runs')
export const getProposalSummary = (id) => client.get(`/runtime-dashboard/proposal-runs/${id}`)
export const deleteProposalRun = (id) => client.delete(`/runtime-dashboard/proposal-runs/${id}`)

export const getRuntimeHealth = () => client.get('/runtime-dashboard/health')

export const getRuntimeOverview = () => client.get('/runtime-dashboard/overview')
