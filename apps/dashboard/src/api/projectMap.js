import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const getProjectMap = () => client.get('/project-map')
export const getProjectMapActivity = () => client.get('/project-map/activity')
export const refreshProjectMap = () => client.post('/project-map/refresh')
