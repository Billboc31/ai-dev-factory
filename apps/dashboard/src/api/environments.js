import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const createEnvironment = (data) => client.post('/environments', data)
export const listEnvironments = () => client.get('/environments')
export const getEnvironment = (id) => client.get(`/environments/${id}`)
export const redeployEnvironment = (id) => client.post(`/environments/${id}/redeploy`)
export const stopEnvironment = (id) => client.post(`/environments/${id}/stop`)
export const deleteEnvironment = (id) => client.delete(`/environments/${id}`)
export const refreshEnvironment = (id) => client.post(`/environments/${id}/refresh`)
export const getEnvironmentLogs = (id) => client.get(`/environments/${id}/logs`)
