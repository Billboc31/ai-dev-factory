import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

const _pfx = (projectId) => projectId ? `/projects/${projectId}` : ''

export const listTickets = (projectId) => client.get(`${_pfx(projectId)}/tickets`)
export const getTicket = (id, projectId) => client.get(`${_pfx(projectId)}/tickets/${id}`)
export const getTicketState = (id, projectId) => client.get(`${_pfx(projectId)}/tickets/${id}/state`)
export const getTicketLogs = (id, projectId) => client.get(`${_pfx(projectId)}/tickets/${id}/logs`)
export const getTicketPlan = (id, projectId) => client.get(`${_pfx(projectId)}/tickets/${id}/plan`)
export const getTicketReview = (id, projectId) => client.get(`${_pfx(projectId)}/tickets/${id}/review`)
export const getTicketTests = (id, projectId) => client.get(`${_pfx(projectId)}/tickets/${id}/tests`)
export const getTicketArtifacts = (id, projectId) => client.get(`${_pfx(projectId)}/tickets/${id}/artifacts`)
export const getTicketTimeline = (id, projectId) => client.get(`${_pfx(projectId)}/tickets/${id}/timeline`)

export const runNextStep = (id, projectId) => client.post(`${_pfx(projectId)}/tickets/${id}/run-next`)
export const approvePlan = (id, projectId) => client.post(`${_pfx(projectId)}/tickets/${id}/approve-plan`)
export const requestPlanFix = (id, projectId) => client.post(`${_pfx(projectId)}/tickets/${id}/request-plan-fix`)
export const approveImplementation = (id, projectId) => client.post(`${_pfx(projectId)}/tickets/${id}/approve-implementation`)
export const requestImplementationFix = (id, projectId) => client.post(`${_pfx(projectId)}/tickets/${id}/request-implementation-fix`)
export const commitChanges = (id, projectId) => client.post(`${_pfx(projectId)}/tickets/${id}/commit`)
export const pushChanges = (id, projectId) => client.post(`${_pfx(projectId)}/tickets/${id}/push`)
export const createCheckpoint = (id, projectId) => client.post(`${_pfx(projectId)}/tickets/${id}/checkpoint`)
export const archiveDaemon = (id, projectId) => client.post(`${_pfx(projectId)}/tickets/${id}/archive`)
export const getAuditLog = (id, projectId) => client.get(`${_pfx(projectId)}/tickets/${id}/audit-log`)
export const markConflictFailed = (id, projectId) => client.post(`${_pfx(projectId)}/tickets/${id}/mark-conflict-failed`)
