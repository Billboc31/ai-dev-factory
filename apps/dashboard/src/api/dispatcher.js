import axios from 'axios'

const client = axios.create({ baseURL: '/api' })

export const getDispatcherStatus = () => client.get('/dispatcher/status')

export const getDispatcherRecommendations = (projectId) =>
  projectId
    ? client.get(`/projects/${projectId}/dispatcher/recommendations`)
    : client.get('/dispatcher/recommendations')
