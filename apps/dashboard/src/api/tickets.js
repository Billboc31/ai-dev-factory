import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const listTickets = () => client.get('/tickets')
export const getTicket = (id) => client.get(`/tickets/${id}`)
export const getTicketLogs = (id) => client.get(`/tickets/${id}/logs`)
export const getTicketPlan = (id) => client.get(`/tickets/${id}/plan`)
export const getTicketReview = (id) => client.get(`/tickets/${id}/review`)
export const getTicketTests = (id) => client.get(`/tickets/${id}/tests`)
export const getTicketArtifacts = (id) => client.get(`/tickets/${id}/artifacts`)

export const runNextStep = (id) => client.post(`/tickets/${id}/run-next`)
export const approvePlan = (id) => client.post(`/tickets/${id}/approve-plan`)
export const requestPlanFix = (id) => client.post(`/tickets/${id}/request-plan-fix`)
export const approveImplementation = (id) => client.post(`/tickets/${id}/approve-implementation`)
export const requestImplementationFix = (id) => client.post(`/tickets/${id}/request-implementation-fix`)
export const commitChanges = (id) => client.post(`/tickets/${id}/commit`)
export const pushChanges = (id) => client.post(`/tickets/${id}/push`)
export const createCheckpoint = (id) => client.post(`/tickets/${id}/checkpoint`)
